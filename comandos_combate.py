import random
import time
import discord
from discord import app_commands

from nucleo import *


class SelectZona(discord.ui.Select):
    def __init__(self, ficha):
        disponibles = [zid for zid in ZONAS_ORDENADAS if zona_lista(ficha, zid)]
        opciones = [
            discord.SelectOption(
                label=ZONAS[zid]["nombre"], value=zid, emoji=ZONAS[zid]["emoji"],
                description=ZONAS[zid]["descripcion"][:100],
            )
            for zid in disponibles
        ]
        super().__init__(placeholder="Elige a dónde ir", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        zona_id = self.values[0]
        if interaction.user.id in BATALLAS_ACTIVAS:
            await interaction.response.send_message(
                "Ya tienes un combate en curso. Termínalo antes de explorar de nuevo.", ephemeral=True
            )
            return
        ficha = obtener_ficha(interaction.user.id, crear=True)
        if not zona_lista(ficha, zona_id):
            await interaction.response.send_message(
                "Esa zona ya no está disponible (EP insuficiente o en enfriamiento).", ephemeral=True
            )
            return

        # El enfriamiento de la zona empieza ya, sin importar como termine el combate
        ficha["cooldowns"][zona_id] = time.time() + ZONAS[zona_id]["cooldown_min"] * 60
        guardar_ficha(interaction.user.id, ficha)

        monstruo_id = elegir_monstruo(zona_id)
        vista = VistaBatalla(self.view.dueno_id, interaction.user, ficha, zona_id, monstruo_id)
        BATALLAS_ACTIVAS.add(self.view.dueno_id)
        m = MONSTRUOS[monstruo_id]
        intro = f'🌍 Exploras **{ZONAS[zona_id]["nombre"]}**... ¡Un **{m["nombre"]}** {m["emoji"]} aparece!'
        vista.interaccion = interaction
        try:
            await interaction.response.edit_message(content=intro, embed=vista.crear_embed(), view=vista)
        except Exception:
            BATALLAS_ACTIVAS.discard(self.view.dueno_id)   # que no quede bloqueado si algo falla
            raise


class VistaZonas(VistaBase):
    def __init__(self, dueno_id, ficha):
        super().__init__(dueno_id)
        self.add_item(SelectZona(ficha))


class SelectHabilidad(discord.ui.Select):
    def __init__(self, batalla):
        opciones = []
        for hid in dict.fromkeys(habilidades_activas(batalla.ficha["habilidades"])):
            h = HABILIDADES[hid]
            detalle = "anula el próximo golpe" if h["tipo"] == "anulacion" else f'daño x{h["multiplicador"]}'
            opciones.append(discord.SelectOption(
                label=h["nombre"], value=hid,
                description=f'{RAREZA_EMOJI[h["rareza"]]} {detalle} · enfriamiento {h["cooldown_rondas"]}t'[:100],
            ))
        super().__init__(placeholder="Usar una habilidad...", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        await self.view.usar_habilidad(interaction, self.values[0])


class SelectPocion(discord.ui.Select):
    def __init__(self, batalla):
        opciones = []
        for clave, cantidad in batalla.ficha["pociones"].items():
            if cantidad <= 0:
                continue
            tipo, nivel_str = clave.rsplit("_", 1)
            opciones.append(discord.SelectOption(
                label=f"{nombre_pocion(tipo, int(nivel_str))} x{cantidad}"[:100],
                value=clave, emoji=EMOJI_TIPO_POCION[tipo],
            ))
        super().__init__(placeholder="Usar una poción...", options=opciones[:25])

    async def callback(self, interaction: discord.Interaction):
        await self.view.usar_pocion(interaction, self.values[0])


class VistaBatalla(VistaBase):
    MAX_TURNOS = 30

    def __init__(self, dueno_id, usuario, ficha, zona_id, monstruo_id):
        super().__init__(dueno_id, timeout=600)
        self.usuario = usuario
        self.ficha = ficha
        self.interaccion = None   # ultima interaccion (para poder cerrar el combate si se agota el tiempo)
        self.raza_id = ficha["raza_id"]
        self.etapa = ficha["etapa"]
        self.zona_id = zona_id
        self.monstruo_id = monstruo_id
        m = MONSTRUOS[monstruo_id]

        mej = ficha["mejoras"]
        self.vida_max_j = round(vida_maxima(self.raza_id, self.etapa) * (1 + mej["vida"] * MEJORA_POR_PUNTO))
        self.energia_max_j = round(energia_maxima(self.raza_id, self.etapa) * (1 + mej["energia"] * MEJORA_POR_PUNTO))
        self.vida_j = self.vida_max_j
        self.energia_j = self.energia_max_j
        self.ataque_j = ataque_base_jugador(self.raza_id, self.etapa)
        self.mult_j = multiplicador_dano(self.raza_id, self.etapa) * (1 + mej["dano"] * MEJORA_POR_PUNTO)
        self.descanso_aplicado = False
        if ficha.get("descansado"):
            self.mult_j *= 1.10
            self.descanso_aplicado = True
            ficha["descansado"] = False
            guardar_ficha(dueno_id, ficha)
        self.mult_especial_extra = 1 + mej["dano_especial"] * MEJORA_POR_PUNTO

        arma_id = ficha["equipado"]["arma"]
        if arma_id and arma_id in ficha["forjados"]:
            self.mult_j *= 1 + BONUS_ARMA.get(ficha["forjados"][arma_id]["rareza"], 0) / 100

        armadura_id = ficha["equipado"]["armadura"]
        bonus_armadura = 0
        if armadura_id and armadura_id in ficha["forjados"]:
            bonus_armadura = BONUS_ARMADURA.get(ficha["forjados"][armadura_id]["rareza"], 0)

        red_puntos = sum(mej["resistencias"].values()) * MEJORA_POR_PUNTO
        self.red_j = min(
            reduccion_dano(self.raza_id, self.etapa, bonus_extra=resistencia_total(ficha["habilidades"]) + bonus_armadura)
            + red_puntos,
            0.75,
        )

        self.vida_max_m = m["vida_max"]
        self.energia_max_m = m["energia_max"]
        self.vida_m = self.vida_max_m
        self.energia_m = self.energia_max_m

        self.defendiendo = False
        self.anulando = False   # si esta activo, anula por completo el proximo golpe recibido
        self.cd_especial_j = 0   # turnos que faltan para poder usar Especial otra vez
        self.cd_especial_m = 0
        self.cd_habilidades = {}   # {id_habilidad: turnos que faltan}
        self.cd_pocion = 0   # turnos que faltan para poder usar otra pocion
        self.turno = 0
        self.terminado = False
        self.log = []

        if habilidades_activas(ficha["habilidades"]):
            self.add_item(SelectHabilidad(self))
        if any(c > 0 for c in ficha["pociones"].values()):
            self.add_item(SelectPocion(self))

    # ---------- utilidades internas ----------
    def _agregar(self, texto):
        self.log.append(f"▸ {texto}")
        self.log = self.log[-5:]

    async def on_timeout(self):
        """Si el jugador abandona el combate, se libera para que pueda volver a explorar."""
        if self.terminado:
            return
        self.terminado = True
        BATALLAS_ACTIVAS.discard(self.dueno_id)
        for item in self.children:
            item.disabled = True
        if self.interaccion is not None:
            try:
                await self.interaccion.edit_original_response(
                    content="⏳ El combate se abandonó por inactividad. Sin recompensas.", view=self
                )
            except discord.HTTPException:
                pass

    def _refrescar_pociones(self):
        """Reconstruye el menu de pociones (quita las que ya se acabaron)."""
        for item in list(self.children):
            if isinstance(item, SelectPocion):
                self.remove_item(item)
        if any(c > 0 for c in self.ficha["pociones"].values()):
            self.add_item(SelectPocion(self))

    def _nombre_j(self):
        return self.usuario.display_name

    def _nombre_m(self):
        m = MONSTRUOS[self.monstruo_id]
        return f'{m["emoji"]} {m["nombre"]}'

    def crear_embed(self, resultado=None):
        m = MONSTRUOS[self.monstruo_id]
        zona = ZONAS[self.zona_id]
        color = 0x2ECC71 if resultado == "victoria" else 0xE74C3C if resultado == "derrota" else 0x3BA9F5
        embed = discord.Embed(title=f"⚔️ {self._nombre_j()} vs {self._nombre_m()}", color=color)
        embed.set_thumbnail(url=self.usuario.display_avatar.url)
        especial_txt = "listo ✅" if self.cd_especial_j == 0 else f"{self.cd_especial_j} turno(s) ⏳"
        linea_tu = (
            f"❤️ {barra(self.vida_j, self.vida_max_j)} **{max(0, self.vida_j):,}**/{self.vida_max_j:,}\n"
            f"⚡ {barra(self.energia_j, self.energia_max_j, tipo='energia')} **{max(0, self.energia_j):,}**/{self.energia_max_j:,}\n"
            f"✨ Especial: {especial_txt}"
        )
        if self.anulando:
            linea_tu += "\n🛡️ Anulación activa: tu próximo golpe recibido no hará daño"
        if any(c > 0 for c in self.ficha["pociones"].values()) or self.cd_pocion > 0:
            pocion_txt = "lista ✅" if self.cd_pocion == 0 else f"{self.cd_pocion} turno(s) ⏳"
            linea_tu += f"\n🧪 Poción: {pocion_txt}"
        if self.descanso_aplicado:
            linea_tu += "\n🛌 Descansado: +10% de daño este combate"
        embed.add_field(name="🧍 Tú", value=linea_tu, inline=False)
        embed.add_field(
            name=self._nombre_m(),
            value=f"❤️ {barra(self.vida_m, self.vida_max_m)} **{max(0, self.vida_m):,}**/{self.vida_max_m:,}\n"
                  f"⚡ {barra(self.energia_m, self.energia_max_m, tipo='energia')} **{max(0, self.energia_m):,}**/{self.energia_max_m:,}",
            inline=False,
        )
        if self.log:
            embed.add_field(name="📜 Registro del combate", value="\n".join(self.log), inline=False)
        embed.set_footer(text=f'{zona["emoji"]} {zona["nombre"]} · Turno {min(self.turno, self.MAX_TURNOS)}/{self.MAX_TURNOS}')
        if m.get("gif"):
            embed.set_image(url=m["gif"])
        return embed

    def _texto_golpe(self, golpe, atacante, objetivo, especial=False, tecnica=None):
        if golpe["fallo"]:
            return random.choice(MENSAJES_FALLO).format(atacante=atacante, objetivo=objetivo)
        if especial:
            texto = random.choice(ATAQUES_ESPECIALES).format(atacante=atacante, objetivo=objetivo, tecnica=tecnica)
        else:
            texto = random.choice(ATAQUES_NORMALES).format(atacante=atacante, objetivo=objetivo)
        texto += f" (-{golpe['dano']} HP)"
        if golpe["critico"]:
            texto += f" {MENSAJES_CRITICO}"
        return texto

    def _turno_monstruo(self):
        """El monstruo actua. Devuelve el texto para el registro."""
        m = MONSTRUOS[self.monstruo_id]
        puede_especial = self.cd_especial_m <= 0 and self.energia_m >= m["especial_costo"]
        usar_especial = puede_especial and random.random() < PROB_ESPECIAL_MONSTRUO
        if usar_especial:
            self.energia_m -= m["especial_costo"]
            self.cd_especial_m = COOLDOWN_ESPECIAL_TURNOS
            golpe = calcular_golpe(m["ataque"], 1.0, self.red_j, factor=1.8,
                                    defendiendo_objetivo=self.defendiendo)
            texto = self._texto_golpe(golpe, self._nombre_m(), self._nombre_j(),
                                       especial=True, tecnica=m["especial_nombre"])
        else:
            golpe = calcular_golpe(m["ataque"], 1.0, self.red_j, defendiendo_objetivo=self.defendiendo)
            texto = self._texto_golpe(golpe, self._nombre_m(), self._nombre_j())
        if not golpe["fallo"]:
            if self.anulando:
                self.anulando = False
                texto += " 🛡️ ¡Pero el golpe fue anulado por completo!"
            else:
                self.vida_j -= golpe["dano"]
        # regeneracion pasiva de energia del monstruo
        self.energia_m = min(self.energia_max_m, self.energia_m + round(self.energia_max_m * 0.08))
        self.defendiendo = False
        return texto

    async def _finalizar(self, interaction, resultado, contenido):
        self.terminado = True
        BATALLAS_ACTIVAS.discard(self.dueno_id)
        for item in self.children:
            item.disabled = True
        self.stop()
        await interaction.response.edit_message(content=contenido, embed=self.crear_embed(resultado), view=self)

    async def _victoria(self, interaction):
        m = MONSTRUOS[self.monstruo_id]
        zona = ZONAS[self.zona_id]
        exp_ganada = round(m["exp"] * zona["mult_exp"])
        ep_ganada = round(m["ep"] * zona["mult_ep"])
        materiales = tirar_materiales(self.monstruo_id)

        ficha = obtener_ficha(self.dueno_id, crear=True)
        ficha["exp"] += exp_ganada
        ficha["ep"] += ep_ganada
        for nombre, cant in materiales.items():
            ficha["materiales"][nombre] = ficha["materiales"].get(nombre, 0) + cant

        objetos_especiales = []
        if random.random() < PROB_HUEVO_HEROE:
            ficha["objetos"].append(OBJETO_HUEVO_HEROE)
            objetos_especiales.append(OBJETO_HUEVO_HEROE)
        if random.random() < PROB_SEMILLA_DEMONIO:
            ficha["objetos"].append(OBJETO_SEMILLA_DEMONIO)
            objetos_especiales.append(OBJETO_SEMILLA_DEMONIO)

        guardar_ficha(self.dueno_id, ficha)

        self._agregar(f"🏆 ¡Derrotaste a {self._nombre_m()}!")
        resumen = (
            f"🏆 **¡Victoria!** Ganaste **{exp_ganada:,} EXP**, **{ep_ganada:,} EP**"
            + (f" y: {materiales_como_texto(materiales)}" if materiales else " y ningún material.")
        )
        if objetos_especiales:
            resumen += f"\n✨ ¡Objeto especial! Encontraste: **{', '.join(objetos_especiales)}**"
        await self._finalizar(interaction, "victoria", resumen)

    async def _derrota(self, interaction):
        self._agregar(f"💀 Has sido derrotado por {self._nombre_m()}.")
        await self._finalizar(interaction, "derrota",
                               "💀 Has sido derrotado. No ganaste recompensas esta vez.")

    async def _procesar_turno(self, interaction, texto_jugador, ataco=True):
        """Aplica el ataque del jugador (si hubo), luego el del monstruo, y actualiza el mensaje."""
        self.interaccion = interaction
        self.turno += 1
        if texto_jugador:
            self._agregar(texto_jugador)

        if self.vida_m <= 0:
            await self._victoria(interaction)
            return

        if ataco:
            texto_m = self._turno_monstruo()
            self._agregar(texto_m)

        if self.vida_j <= 0:
            await self._derrota(interaction)
            return

        if self.turno >= self.MAX_TURNOS:
            self._agregar("⏳ El combate se alarga demasiado y ambos se retiran.")
            await self._finalizar(interaction, None, "⏳ Combate terminado por tiempo. Sin recompensas.")
            return

        # El round se completo: bajar los enfriamientos de especial y de habilidades
        if self.cd_especial_j > 0:
            self.cd_especial_j -= 1
        if self.cd_especial_m > 0:
            self.cd_especial_m -= 1
        for hid in list(self.cd_habilidades):
            if self.cd_habilidades[hid] > 0:
                self.cd_habilidades[hid] -= 1
        if self.cd_pocion > 0:
            self.cd_pocion -= 1

        await interaction.response.edit_message(embed=self.crear_embed(), view=self)

    # ---------- botones ----------
    @discord.ui.button(label="Atacar", emoji="⚔️", style=discord.ButtonStyle.primary)
    async def atacar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.terminado:
            return
        golpe = calcular_golpe(self.ataque_j, self.mult_j, 0.0)
        texto = self._texto_golpe(golpe, self._nombre_j(), self._nombre_m())
        if not golpe["fallo"]:
            self.vida_m -= golpe["dano"]
        self.energia_j = min(self.energia_max_j, self.energia_j + round(self.energia_max_j * 0.06))
        await self._procesar_turno(interaction, texto)

    @discord.ui.button(label="Especial", emoji="✨", style=discord.ButtonStyle.primary)
    async def especial(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.terminado:
            return
        if self.cd_especial_j > 0:
            await interaction.response.send_message(
                f"Tu especial está en enfriamiento: {self.cd_especial_j} turno(s) más.", ephemeral=True
            )
            return
        costo = round(self.energia_max_j * 0.35)
        if self.energia_j < costo:
            await interaction.response.send_message("No tienes suficiente energía para un especial.", ephemeral=True)
            return
        self.energia_j -= costo
        self.cd_especial_j = COOLDOWN_ESPECIAL_TURNOS
        golpe = calcular_golpe(self.ataque_j, self.mult_j, 0.0, factor=1.8 * self.mult_especial_extra)
        texto = self._texto_golpe(golpe, self._nombre_j(), self._nombre_m(), especial=True, tecnica="Ataque Especial")
        if not golpe["fallo"]:
            self.vida_m -= golpe["dano"]
        await self._procesar_turno(interaction, texto)

    @discord.ui.button(label="Defender", emoji="🛡️", style=discord.ButtonStyle.secondary)
    async def defender(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.terminado:
            return
        self.defendiendo = True
        self.energia_j = min(self.energia_max_j, self.energia_j + round(self.energia_max_j * 0.15))
        texto = f"{self._nombre_j()} se pone en guardia, reduciendo el próximo golpe recibido."
        await self._procesar_turno(interaction, texto)

    @discord.ui.button(label="Huir", emoji="🏃", style=discord.ButtonStyle.danger)
    async def huir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.terminado:
            return
        self._agregar(f"🏃 {self._nombre_j()} huye del combate.")
        await self._finalizar(interaction, None, "🏃 Escapaste del combate. No hubo recompensas ni penalización.")

    # ---------- usar una habilidad (desde el SelectHabilidad) ----------
    async def usar_habilidad(self, interaction: discord.Interaction, hid: str):
        if self.terminado:
            return
        h = HABILIDADES[hid]
        cd_actual = self.cd_habilidades.get(hid, 0)
        if cd_actual > 0:
            await interaction.response.send_message(
                f"**{h['nombre']}** está en enfriamiento: {cd_actual} ronda(s) más.", ephemeral=True
            )
            return

        if h["tipo"] == "ofensiva":
            costo = h.get("costo_energia", 0)
            if self.energia_j < costo:
                await interaction.response.send_message(
                    f"No tienes suficiente energía para usar **{h['nombre']}**.", ephemeral=True
                )
                return
            self.energia_j -= costo
            self.cd_habilidades[hid] = h["cooldown_rondas"]
            golpe = calcular_golpe(self.ataque_j, self.mult_j, 0.0, factor=h["multiplicador"] * self.mult_especial_extra)
            texto = self._texto_golpe(golpe, self._nombre_j(), self._nombre_m(), especial=True, tecnica=h["nombre"])
            if not golpe["fallo"]:
                self.vida_m -= golpe["dano"]
            await self._procesar_turno(interaction, texto)

        elif h["tipo"] == "anulacion":
            self.anulando = True
            self.cd_habilidades[hid] = h["cooldown_rondas"]
            texto = f"{self._nombre_j()} activa **{h['nombre']}**, lista para anular el próximo golpe."
            await self._procesar_turno(interaction, texto)

        else:
            await interaction.response.send_message("Esa habilidad no se usa así en combate.", ephemeral=True)

    async def usar_pocion(self, interaction: discord.Interaction, clave: str):
        if self.terminado:
            return
        if self.cd_pocion > 0:
            await interaction.response.send_message(
                f"Las pociones están en enfriamiento: {self.cd_pocion} turno(s) más.", ephemeral=True
            )
            return
        ficha = obtener_ficha(self.dueno_id, crear=True)
        if ficha["pociones"].get(clave, 0) <= 0:
            await interaction.response.send_message("Ya no tienes esa poción.", ephemeral=True)
            return
        tipo, nivel_str = clave.rsplit("_", 1)
        nivel = int(nivel_str)
        ficha["pociones"][clave] -= 1
        if ficha["pociones"][clave] <= 0:
            del ficha["pociones"][clave]
        guardar_ficha(self.dueno_id, ficha)
        self.cd_pocion = COOLDOWN_POCION_RONDAS

        if tipo == "vida":
            curado = round(self.vida_max_j * nivel / 100)
            self.vida_j = min(self.vida_max_j, self.vida_j + curado)
            texto = f"🧪 {self._nombre_j()} bebe {nombre_pocion(tipo, nivel)} y recupera {curado} de vida."
        elif tipo == "energia":
            recuperado = round(self.energia_max_j * nivel / 100)
            self.energia_j = min(self.energia_max_j, self.energia_j + recuperado)
            texto = f"🧪 {self._nombre_j()} bebe {nombre_pocion(tipo, nivel)} y recupera {recuperado} de energía."
        else:
            self.mult_j *= (1 + nivel / 100)
            texto = f"🧪 {self._nombre_j()} bebe {nombre_pocion(tipo, nivel)}: su daño sube {nivel}% el resto del combate."

        self._refrescar_pociones()
        await self._procesar_turno(interaction, texto)

@bot.tree.command(name="explorar", description="Explora el continente y busca un combate")
@app_commands.guild_only()
async def explorar(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if not ficha["raza_id"]:
        await interaction.response.send_message("Primero elige tu raza con /raza.", ephemeral=True)
        return
    if interaction.user.id in BATALLAS_ACTIVAS:
        await interaction.response.send_message(
            "Ya tienes un combate en curso. Termínalo antes de explorar de nuevo.", ephemeral=True
        )
        return

    disponibles = [zid for zid in ZONAS_ORDENADAS if zona_lista(ficha, zid)]
    embed = discord.Embed(title="🗺️ Zonas del continente", description=texto_zonas(ficha), color=0x3BA9F5)
    embed.set_footer(text=f"Tu EP: {ficha['ep']:,}")
    if not disponibles:
        embed.add_field(
            name="⏳ Sin zonas disponibles",
            value="Espera a que termine algún enfriamiento para volver a explorar.",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    await interaction.response.send_message(embed=embed, view=VistaZonas(interaction.user.id, ficha))

