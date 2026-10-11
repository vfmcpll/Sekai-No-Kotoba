# ============================================================
#  MAIN - Arranque del bot + comandos de perfil, admin y arena PvP
#  Comandos: /raza (al azar) /perfil /evolucionar /evolucion_definitiva /mejorar
#            /habilidad /habilidades /diario /entrenar /pagar /top
#            /arena desafiar /arena ranking
#            /configuracion (panel del dueño del servidor)
#            /admin_* (solo dueño + las personas/roles que el dueño elija)
#  Opcional en Railway: ADMIN_ID = tu ID de Discord (admin extra fijo).
# ============================================================
import copy
import os
import random
import traceback
from datetime import date, timedelta

import discord
from discord import app_commands

from nucleo import *
import comandos_ciudad
import comandos_combate
import comandos_trade
from habilidades import texto_habilidad


# ============================================================
#  QUIEN ES ADMIN DEL BOT
#  El dueño del servidor siempre. Ademas, las personas y roles que el
#  dueño elija en /configuracion (y, si existe, el ADMIN_ID de Railway).
# ============================================================
def es_admin_unico(interaction: discord.Interaction) -> bool:
    if es_dueno_servidor(interaction):
        return True
    admin_id = os.getenv("ADMIN_ID", "").strip()
    if admin_id.isdigit() and interaction.user.id == int(admin_id):
        return True
    conf = config_guild(interaction.guild_id)
    if interaction.user.id in conf.get("admin_usuarios", []):
        return True
    ids_roles = set(conf.get("admin_roles", []))
    return any(r.id in ids_roles for r in getattr(interaction.user, "roles", []))


async def exigir_admin(interaction: discord.Interaction) -> bool:
    if es_admin_unico(interaction):
        return True
    await interaction.response.send_message(
        "🚫 No tienes permiso para este comando. El dueño del servidor decide quién es admin con /configuracion.",
        ephemeral=True,
    )
    return False


# ============================================================
#  UTILIDADES
# ============================================================
class VistaConfirmar(VistaBase):
    """Botones Confirmar / Cancelar. 'accion' es una funcion async que recibe la interaccion."""

    def __init__(self, dueno_id, accion):
        super().__init__(dueno_id, timeout=60)
        self.accion = accion

    @discord.ui.button(label="Confirmar", emoji="✅", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await self.accion(interaction)

    @discord.ui.button(label="Cancelar", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Cancelado.", embed=None, view=None)


def _pvp(ficha):
    p = ficha.setdefault("pvp", {})
    p.setdefault("victorias", 0)
    p.setdefault("derrotas", 0)
    return p


# ============================================================
#  /raza  -> tu raza sale AL AZAR
#  Tienes 3 tiradas en total (la primera te la asigna; puedes volver a tirar 2 veces).
#  Las razas dificiles son mas raras. Al evolucionar o ganar EXP ya no se puede cambiar.
# ============================================================
TIRADAS_RAZA_MAX = 3
PESOS_DIFICULTAD_RAZA = {1: 30, 2: 30, 3: 20, 4: 12, 5: 8}   # a mas dificil, mas rara


def tirar_raza(excluir=None):
    ids = [rid for rid, r in RAZAS.items() if r["cat"] in CATEGORIAS and rid != excluir]
    pesos = [PESOS_DIFICULTAD_RAZA.get(RAZAS[i]["dificultad"], 10) for i in ids]
    return random.choices(ids, weights=pesos)[0]


def asignar_raza(ficha, rid):
    anterior = RAZAS.get(ficha["raza_id"])
    ep_anterior = anterior["ep_inicial"] if anterior else 0
    ficha["raza_id"] = rid
    ficha["raza"] = RAZAS[rid]["nombre"]
    ficha["etapa"] = 0
    ficha["ep"] = max(0, ficha["ep"] - ep_anterior + RAZAS[rid]["ep_inicial"])


def embed_tirada_raza(rid, ficha):
    embed = embed_raza(rid)
    embed.title = f'🎲 ¡Te tocó: {RAZAS[rid]["emoji"]} {RAZAS[rid]["nombre"]}!'
    restantes = TIRADAS_RAZA_MAX - ficha.get("tiradas_raza", 0)
    embed.set_footer(text=f"Tiradas restantes: {restantes} · Cuando ganes EXP tu raza queda fija.")
    return embed


class VistaRazaAzar(VistaBase):
    def __init__(self, dueno_id, ficha):
        super().__init__(dueno_id)
        self.volver.disabled = ficha.get("tiradas_raza", 0) >= TIRADAS_RAZA_MAX
        self.volver.label = f'Volver a tirar ({TIRADAS_RAZA_MAX - ficha.get("tiradas_raza", 0)})'

    @discord.ui.button(label="Volver a tirar", emoji="🎲", style=discord.ButtonStyle.primary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        if ya_evoluciono(ficha) or ficha.get("tiradas_raza", 0) >= TIRADAS_RAZA_MAX:
            await interaction.response.edit_message(content="Tu raza ya quedó fija.", embed=None, view=None)
            return
        rid = tirar_raza(excluir=ficha["raza_id"])
        asignar_raza(ficha, rid)
        ficha["tiradas_raza"] = ficha.get("tiradas_raza", 0) + 1
        guardar_ficha(self.dueno_id, ficha)
        await interaction.response.edit_message(
            content=None, embed=embed_tirada_raza(rid, ficha), view=VistaRazaAzar(self.dueno_id, ficha)
        )

    @discord.ui.button(label="Quedarme con esta", emoji="✅", style=discord.ButtonStyle.success)
    async def quedarme(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        ficha["tiradas_raza"] = TIRADAS_RAZA_MAX   # decidido: ya no se puede volver a tirar
        guardar_ficha(self.dueno_id, ficha)
        await interaction.response.edit_message(
            content=f'🌟 ¡Listo! Eres **{ficha["raza"]}**. Usa /perfil para ver tu personaje y /explorar para salir a pelear.',
            embed=embed_raza(ficha["raza_id"]), view=None,
        )


@bot.tree.command(name="raza", description="Crea tu personaje: tu raza sale al azar")
@app_commands.guild_only()
async def raza(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if ficha["raza_id"] and (ya_evoluciono(ficha) or ficha.get("tiradas_raza", 0) >= TIRADAS_RAZA_MAX):
        await interaction.response.send_message(
            "Tu raza ya quedó fija. Esta es:", embed=embed_raza(ficha["raza_id"]), ephemeral=True
        )
        return
    if not ficha["raza_id"]:
        asignar_raza(ficha, tirar_raza())
        ficha["tiradas_raza"] = 1
        guardar_ficha(interaction.user.id, ficha)
    await interaction.response.send_message(
        embed=embed_tirada_raza(ficha["raza_id"], ficha),
        view=VistaRazaAzar(interaction.user.id, ficha), ephemeral=True,
    )


# ============================================================
#  /perfil
# ============================================================
@bot.tree.command(name="perfil", description="Mira tu perfil (o el de otro jugador)")
@app_commands.describe(usuario="De quién quieres ver el perfil (vacío = el tuyo)")
@app_commands.guild_only()
async def perfil(interaction: discord.Interaction, usuario: discord.Member = None):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    objetivo = usuario or interaction.user
    ficha = obtener_ficha(objetivo.id, crear=(objetivo.id == interaction.user.id))
    if ficha is None:
        await interaction.response.send_message(f"{objetivo.display_name} todavía no tiene personaje.", ephemeral=True)
        return
    if objetivo.id == interaction.user.id and not ficha["raza_id"]:
        await interaction.response.send_message(
            "Aún no tienes personaje. Usa **/raza** para crearlo.", ephemeral=True
        )
        return
    await interaction.response.send_message(embed=crear_embed_perfil(objetivo, ficha))


# ============================================================
#  /evolucionar
# ============================================================
@bot.tree.command(name="evolucionar", description="Evoluciona tu raza a la siguiente etapa")
@app_commands.guild_only()
async def evolucionar(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    rid = ficha["raza_id"]
    if rid not in RAZAS:
        await interaction.response.send_message("Primero elige tu raza con /raza.", ephemeral=True)
        return
    etapa = ficha["etapa"]
    necesaria = exp_necesaria(rid, etapa)
    if necesaria is None:
        extra = "" if rid in RAZAS_TRASCENDENTES else " Si cumples los requisitos, puedes usar /evolucion_definitiva."
        await interaction.response.send_message(f"Ya estás en tu etapa máxima.{extra}", ephemeral=True)
        return
    if ficha["exp"] < necesaria:
        await interaction.response.send_message(
            f'Te falta experiencia: tienes {ficha["exp"]:,} de {necesaria:,}.', ephemeral=True
        )
        return
    ep_req = ep_min_necesario(rid, etapa)
    if ep_req and ficha["ep"] < ep_req:
        await interaction.response.send_message(
            f'Esta evolución también pide {ep_req:,} EP y tienes {ficha["ep"]:,}.', ephemeral=True
        )
        return
    ganado = ep_al_evolucionar(rid, etapa)
    ficha["exp"] -= necesaria
    ficha["ep"] += ganado
    ficha["etapa"] = etapa + 1
    ficha["raza"] = nombre_etapa(rid, ficha["etapa"])
    guardar_ficha(interaction.user.id, ficha)
    await interaction.response.send_message(
        f'✨ **{interaction.user.display_name}** evolucionó a **{ficha["raza"]}** y ganó **{ganado:,} EP**.'
    )


# ============================================================
#  /evolucion_definitiva  (Héroe Verdadero / Rey Demonio Verdadero)
# ============================================================
DESTINOS_TRASCENDER = {
    "heroe": ("heroe_verdadero", OBJETO_HUEVO_HEROE),
    "demonio": ("rey_demonio_verdadero", OBJETO_SEMILLA_DEMONIO),
}


def _error_trascender(ficha, destino_clave):
    rid = ficha["raza_id"]
    if rid not in RAZAS:
        return "Primero elige tu raza con /raza."
    if rid in RAZAS_TRASCENDENTES:
        return "Ya trascendiste. Es una forma definitiva."
    if exp_necesaria(rid, ficha["etapa"]) is not None:
        return "Primero debes llegar a la evolución máxima de tu raza."
    if ficha["ep"] < EP_MINIMO_TRASCENDER:
        return f'Necesitas al menos {EP_MINIMO_TRASCENDER:,} EP (tienes {ficha["ep"]:,}). No se gastan.'
    if ficha["exp"] < EXP_COSTO_TRASCENDER:
        return f'Necesitas {EXP_COSTO_TRASCENDER:,} EXP (tienes {ficha["exp"]:,}). Se gastan.'
    objeto = DESTINOS_TRASCENDER[destino_clave][1]
    if objeto not in ficha["objetos"]:
        return f"Necesitas tener el objeto **{objeto}**."
    return None


@bot.tree.command(name="evolucion_definitiva", description="Trasciende a Héroe Verdadero o Rey Demonio Verdadero")
@app_commands.describe(camino="A qué forma quieres trascender")
@app_commands.choices(camino=[
    app_commands.Choice(name="Héroe Verdadero (Huevo de Héroe)", value="heroe"),
    app_commands.Choice(name="Rey Demonio Verdadero (Semilla de Rey Demonio)", value="demonio"),
])
@app_commands.guild_only()
async def evolucion_definitiva(interaction: discord.Interaction, camino: app_commands.Choice[str]):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    error = _error_trascender(ficha, camino.value)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return
    destino, objeto = DESTINOS_TRASCENDER[camino.value]

    async def accion(inter: discord.Interaction):
        f = obtener_ficha(interaction.user.id, crear=True)
        err = _error_trascender(f, camino.value)
        if err:
            await inter.response.edit_message(content=err, embed=None, view=None)
            return
        f["objetos"].remove(objeto)
        f["exp"] -= EXP_COSTO_TRASCENDER
        f["raza_id"] = destino
        f["raza"] = RAZAS[destino]["nombre"]
        f["etapa"] = 0
        guardar_ficha(interaction.user.id, f)
        await inter.response.edit_message(
            content=f'🌟 ¡**{interaction.user.display_name}** trascendió y ahora es **{RAZAS[destino]["nombre"]}**!',
            embed=embed_raza(destino), view=None,
        )

    await interaction.response.send_message(
        f'⚠️ Vas a trascender a **{RAZAS[destino]["nombre"]}**. Se gastan {EXP_COSTO_TRASCENDER:,} EXP y tu {objeto}. '
        "**No se puede deshacer.** ¿Confirmas?",
        view=VistaConfirmar(interaction.user.id, accion), ephemeral=True,
    )


# ============================================================
#  /mejorar  (gastar puntos de estadísticas)
# ============================================================
@bot.tree.command(name="mejorar", description="Gasta tus puntos para mejorar una estadística")
@app_commands.describe(
    estadistica="Qué quieres mejorar", cantidad="Cuántos puntos gastar",
    elemento="Solo si elegiste Resistencia: contra qué elemento",
)
@app_commands.choices(
    estadistica=[
        app_commands.Choice(name="Daño", value="dano"),
        app_commands.Choice(name="Daño especial", value="dano_especial"),
        app_commands.Choice(name="Vida", value="vida"),
        app_commands.Choice(name="Energía", value="energia"),
        app_commands.Choice(name="Resistencia (elige elemento)", value="resistencia"),
    ],
    elemento=[app_commands.Choice(name=e, value=e) for e in ELEMENTOS_RESISTENCIA],
)
@app_commands.guild_only()
async def mejorar(
    interaction: discord.Interaction,
    estadistica: app_commands.Choice[str],
    cantidad: app_commands.Range[int, 1, 1_000_000],
    elemento: app_commands.Choice[str] = None,
):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if not ficha["raza_id"]:
        await interaction.response.send_message("Primero elige tu raza con /raza.", ephemeral=True)
        return
    if estadistica.value == "resistencia" and elemento is None:
        await interaction.response.send_message("Elige también el elemento de la resistencia.", ephemeral=True)
        return
    disponibles = puntos_disponibles(ficha)
    if cantidad > disponibles:
        await interaction.response.send_message(
            f"No tienes tantos puntos: te quedan {disponibles:,}. (Ganas 1 cada {PUNTOS_POR_EP} EP.)", ephemeral=True
        )
        return
    m = ficha["mejoras"]
    if estadistica.value == "resistencia":
        m["resistencias"][elemento.value] = m["resistencias"].get(elemento.value, 0) + cantidad
        nombre = f"Resistencia a {elemento.value}"
    else:
        m[estadistica.value] += cantidad
        nombre = estadistica.name
    guardar_ficha(interaction.user.id, ficha)
    await interaction.response.send_message(
        f"📊 Gastaste **{cantidad:,}** punto(s) en **{nombre}** (+{pct(cantidad)}%). Te quedan {puntos_disponibles(ficha):,}.",
        ephemeral=True,
    )


# ============================================================
#  /habilidad (Roll / Ruleta) y /habilidades
# ============================================================
@bot.tree.command(name="habilidad", description="Tira por una habilidad nueva (cuesta dinero)")
@app_commands.describe(modo="Roll es barato; la Ruleta es cara pero da mejores habilidades")
@app_commands.choices(modo=[
    app_commands.Choice(name=f"Roll ({COSTO_ROLL:,})", value="roll"),
    app_commands.Choice(name=f"Ruleta ({COSTO_RULETA:,})", value="ruleta"),
])
@app_commands.guild_only()
async def habilidad(interaction: discord.Interaction, modo: app_commands.Choice[str]):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if not ficha["raza_id"]:
        await interaction.response.send_message("Primero elige tu raza con /raza.", ephemeral=True)
        return
    costo = COSTO_ROLL if modo.value == "roll" else COSTO_RULETA
    pesos = PESOS_ROLL if modo.value == "roll" else PESOS_RULETA
    if ficha["dinero"] < costo:
        await interaction.response.send_message(
            f'Necesitas {moneda(interaction.guild_id, costo)} y tienes {moneda(interaction.guild_id, ficha["dinero"])}.',
            ephemeral=True,
        )
        return
    ficha["dinero"] -= costo
    hid = tirar_habilidad(pesos)
    ficha["habilidades"].append(hid)
    guardar_ficha(interaction.user.id, ficha)
    h = HABILIDADES[hid]
    embed = discord.Embed(
        title=f'{RAREZA_EMOJI[h["rareza"]]} {h["nombre"]}',
        description=f'{h["descripcion"]}\n\n{texto_habilidad(h)}',
        color=RAREZA_COLOR[h["rareza"]],
    )
    embed.set_footer(text=f'Rareza {RAREZA_NOMBRE[h["rareza"]]} · Gastaste {costo:,}')
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="habilidades", description="Mira qué hace cada una de tus habilidades")
@app_commands.guild_only()
async def habilidades(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    conteo = {}
    for hid in ficha["habilidades"]:
        if hid in HABILIDADES:
            conteo[hid] = conteo.get(hid, 0) + 1
    if not conteo:
        await interaction.response.send_message("Todavía no tienes habilidades. Prueba /habilidad.", ephemeral=True)
        return
    orden = sorted(conteo, key=lambda h: (-ORDEN_RAREZA[HABILIDADES[h]["rareza"]], HABILIDADES[h]["nombre"]))
    lineas = []
    for hid in orden:
        h = HABILIDADES[hid]
        x = f" ×{conteo[hid]}" if conteo[hid] > 1 else ""
        lineas.append(f'{RAREZA_EMOJI[h["rareza"]]} **{h["nombre"]}**{x}\n   {texto_habilidad(h)}')
    embed = discord.Embed(title="✨ Tus habilidades", description="\n".join(lineas)[:4000], color=0x3BA9F5)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================================
#  ARENA PVP
# ============================================================
class Luchador:
    """Copia de las estadisticas de un jugador para un duelo (no toca su ficha)."""

    def __init__(self, miembro, ficha):
        self.id = miembro.id
        self.nombre = miembro.display_name
        raza_id, etapa = ficha["raza_id"], ficha["etapa"]
        mej = ficha["mejoras"]
        self.vida_max = round(vida_maxima(raza_id, etapa) * (1 + mej["vida"] * MEJORA_POR_PUNTO))
        self.energia_max = round(energia_maxima(raza_id, etapa) * (1 + mej["energia"] * MEJORA_POR_PUNTO))
        self.vida = self.vida_max
        self.energia = self.energia_max
        self.ataque = ataque_base_jugador(raza_id, etapa)
        self.mult = multiplicador_dano(raza_id, etapa) * (1 + mej["dano"] * MEJORA_POR_PUNTO)
        self.mult_especial = 1 + mej["dano_especial"] * MEJORA_POR_PUNTO

        arma_id = ficha["equipado"]["arma"]
        if arma_id and arma_id in ficha["forjados"]:
            self.mult *= 1 + BONUS_ARMA.get(ficha["forjados"][arma_id]["rareza"], 0) / 100
        armadura_id = ficha["equipado"]["armadura"]
        bonus_armadura = 0
        if armadura_id and armadura_id in ficha["forjados"]:
            bonus_armadura = BONUS_ARMADURA.get(ficha["forjados"][armadura_id]["rareza"], 0)
        red_puntos = sum(mej["resistencias"].values()) * MEJORA_POR_PUNTO
        self.red = min(
            reduccion_dano(raza_id, etapa, bonus_extra=resistencia_total(ficha["habilidades"]) + bonus_armadura) + red_puntos,
            0.75,
        )
        self.defendiendo = False
        self.cd_especial = 0


class VistaDuelo(discord.ui.View):
    MAX_TURNOS = 40   # turnos en total (20 por jugador); si nadie cae, gana quien tenga mas vida %

    def __init__(self, a, b, apuesta, guild_id):
        super().__init__(timeout=180)
        self.luchadores = [a, b]
        self.idx = random.randint(0, 1)
        self.apuesta = apuesta
        self.guild_id = guild_id
        self.turno = 0
        self.log = []
        self.terminado = False
        self.interaccion = None

    @property
    def actual(self):
        return self.luchadores[self.idx]

    @property
    def otro(self):
        return self.luchadores[1 - self.idx]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.luchadores[0].id, self.luchadores[1].id):
            await interaction.response.send_message("Este duelo no es tuyo.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        await avisar_error(interaction)

    def _agregar(self, texto):
        self.log.append(f"▸ {texto}")
        self.log = self.log[-5:]

    async def _es_su_turno(self, interaction):
        if self.terminado:
            return False
        if interaction.user.id != self.actual.id:
            await interaction.response.send_message("Todavía no es tu turno.", ephemeral=True)
            return False
        return True

    def crear_embed(self, final=False):
        a, b = self.luchadores
        embed = discord.Embed(title=f"⚔️ Arena: {a.nombre} vs {b.nombre}", color=0xE67E22)
        if not final:
            embed.description = f"🎯 Turno de **{self.actual.nombre}**"
        for l in (a, b):
            especial = "listo ✅" if l.cd_especial == 0 else f"{l.cd_especial} turno(s) ⏳"
            embed.add_field(
                name=l.nombre,
                value=(
                    f"❤️ {barra(l.vida, l.vida_max)} **{max(0, l.vida):,}**/{l.vida_max:,}\n"
                    f"⚡ {barra(l.energia, l.energia_max, tipo='energia')} **{max(0, l.energia):,}**/{l.energia_max:,}\n"
                    f"✨ Especial: {especial}"
                ),
                inline=False,
            )
        if self.log:
            embed.add_field(name="📜 Registro", value="\n".join(self.log), inline=False)
        pie = f"Turno {min(self.turno, self.MAX_TURNOS)}/{self.MAX_TURNOS}"
        if self.apuesta:
            pie += f" · Apuesta: {self.apuesta:,}"
        embed.set_footer(text=pie)
        return embed

    def _texto_golpe(self, golpe, atacante, objetivo, especial=False):
        if golpe["fallo"]:
            return random.choice(MENSAJES_FALLO).format(atacante=atacante, objetivo=objetivo)
        if especial:
            texto = random.choice(ATAQUES_ESPECIALES).format(atacante=atacante, objetivo=objetivo, tecnica="Ataque Especial")
        else:
            texto = random.choice(ATAQUES_NORMALES).format(atacante=atacante, objetivo=objetivo)
        texto += f" (-{golpe['dano']} HP)"
        if golpe["critico"]:
            texto += f" {MENSAJES_CRITICO}"
        return texto

    async def _cerrar_turno(self, interaction, texto):
        self.interaccion = interaction
        a, o = self.actual, self.otro
        o.defendiendo = False   # la guardia del rival solo dura hasta que tu actuas
        self.turno += 1
        self._agregar(texto)
        if a.cd_especial > 0:
            a.cd_especial -= 1
        if o.vida <= 0:
            await self._terminar(interaction, a, o)
            return
        if self.turno >= self.MAX_TURNOS:
            fa = self.luchadores[0].vida / self.luchadores[0].vida_max
            fb = self.luchadores[1].vida / self.luchadores[1].vida_max
            if fa == fb:
                await self._terminar(interaction, None, None, " (empate por tiempo)")
            else:
                ganador, perdedor = (self.luchadores[0], self.luchadores[1]) if fa > fb else (self.luchadores[1], self.luchadores[0])
                await self._terminar(interaction, ganador, perdedor, " por tiempo")
            return
        self.idx = 1 - self.idx
        await interaction.response.edit_message(embed=self.crear_embed(), view=self)

    async def _terminar(self, interaction, ganador, perdedor, motivo=""):
        self.terminado = True
        self.stop()
        for l in self.luchadores:
            BATALLAS_ACTIVAS.discard(l.id)
        for item in self.children:
            item.disabled = True
        if ganador is not None:
            fg = obtener_ficha(ganador.id, crear=True)
            fp = obtener_ficha(perdedor.id, crear=True)
            _pvp(fg)["victorias"] += 1
            _pvp(fp)["derrotas"] += 1
            cantidad = min(self.apuesta, fp["dinero"])
            fp["dinero"] -= cantidad
            fg["dinero"] += cantidad
            guardar_ficha(ganador.id, fg)
            guardar_ficha(perdedor.id, fp)
            texto = f"🏆 **{ganador.nombre}** gana el duelo{motivo}."
            if cantidad:
                texto += f" Se lleva {moneda(self.guild_id, cantidad)}."
        else:
            texto = f"🤝 El duelo termina en empate{motivo.replace(' (empate por tiempo)', '')}. Nadie pierde nada."
        embed = self.crear_embed(final=True)
        if interaction is not None:
            await interaction.response.edit_message(content=texto, embed=embed, view=self)
        elif self.interaccion is not None:
            try:
                await self.interaccion.edit_original_response(content=texto, embed=embed, view=self)
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        if self.terminado:
            return
        await self._terminar(None, self.otro, self.actual, " (el otro se quedó sin responder)")

    @discord.ui.button(label="Atacar", emoji="⚔️", style=discord.ButtonStyle.primary)
    async def atacar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._es_su_turno(interaction):
            return
        a, o = self.actual, self.otro
        golpe = calcular_golpe(a.ataque, a.mult, o.red, defendiendo_objetivo=o.defendiendo)
        texto = self._texto_golpe(golpe, a.nombre, o.nombre)
        if not golpe["fallo"]:
            o.vida -= golpe["dano"]
        a.energia = min(a.energia_max, a.energia + round(a.energia_max * 0.06))
        await self._cerrar_turno(interaction, texto)

    @discord.ui.button(label="Especial", emoji="✨", style=discord.ButtonStyle.primary)
    async def especial(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._es_su_turno(interaction):
            return
        a, o = self.actual, self.otro
        if a.cd_especial > 0:
            await interaction.response.send_message(f"Tu especial está en enfriamiento: {a.cd_especial} turno(s).", ephemeral=True)
            return
        costo = round(a.energia_max * 0.35)
        if a.energia < costo:
            await interaction.response.send_message("No tienes suficiente energía para un especial.", ephemeral=True)
            return
        a.energia -= costo
        a.cd_especial = COOLDOWN_ESPECIAL_TURNOS
        golpe = calcular_golpe(a.ataque, a.mult, o.red, factor=1.8 * a.mult_especial, defendiendo_objetivo=o.defendiendo)
        texto = self._texto_golpe(golpe, a.nombre, o.nombre, especial=True)
        if not golpe["fallo"]:
            o.vida -= golpe["dano"]
        await self._cerrar_turno(interaction, texto)

    @discord.ui.button(label="Defender", emoji="🛡️", style=discord.ButtonStyle.secondary)
    async def defender(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._es_su_turno(interaction):
            return
        a = self.actual
        a.defendiendo = True
        a.energia = min(a.energia_max, a.energia + round(a.energia_max * 0.15))
        await self._cerrar_turno(interaction, f"{a.nombre} se pone en guardia, reduciendo el próximo golpe.")

    @discord.ui.button(label="Rendirse", emoji="🏳️", style=discord.ButtonStyle.danger)
    async def rendirse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.terminado:
            return
        quien = next(l for l in self.luchadores if l.id == interaction.user.id)
        rival = next(l for l in self.luchadores if l.id != interaction.user.id)
        self._agregar(f"🏳️ {quien.nombre} se rinde.")
        await self._terminar(interaction, rival, quien, " (por rendición)")


class VistaDesafio(discord.ui.View):
    def __init__(self, retador, rival, apuesta, guild_id):
        super().__init__(timeout=120)
        self.retador = retador
        self.rival = rival
        self.apuesta = apuesta
        self.guild_id = guild_id
        self.interaccion = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.retador.id, self.rival.id):
            await interaction.response.send_message("Este desafío no es tuyo.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        await avisar_error(interaction)

    async def on_timeout(self):
        if self.interaccion is not None:
            try:
                await self.interaccion.edit_original_response(content="⏳ El desafío expiró sin respuesta.", embed=None, view=None)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Aceptar", emoji="⚔️", style=discord.ButtonStyle.success)
    async def aceptar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.rival.id:
            await interaction.response.send_message("Solo el retado puede aceptar.", ephemeral=True)
            return
        if self.retador.id in BATALLAS_ACTIVAS or self.rival.id in BATALLAS_ACTIVAS:
            await interaction.response.send_message("Alguno de los dos ya está en un combate.", ephemeral=True)
            return
        fa = obtener_ficha(self.retador.id, crear=True)
        fb = obtener_ficha(self.rival.id, crear=True)
        if self.apuesta and (fa["dinero"] < self.apuesta or fb["dinero"] < self.apuesta):
            await interaction.response.edit_message(
                content="❌ Alguno de los dos ya no tiene dinero para la apuesta. Desafío cancelado.", embed=None, view=None
            )
            self.stop()
            return
        self.stop()
        duelo = VistaDuelo(Luchador(self.retador, fa), Luchador(self.rival, fb), self.apuesta, self.guild_id)
        duelo.interaccion = interaction
        BATALLAS_ACTIVAS.add(self.retador.id)
        BATALLAS_ACTIVAS.add(self.rival.id)
        await interaction.response.edit_message(
            content=f"⚔️ ¡Comienza el duelo! {self.retador.mention} vs {self.rival.mention}",
            embed=duelo.crear_embed(), view=duelo,
        )

    @discord.ui.button(label="Rechazar", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.rival.id:
            await interaction.response.send_message("Solo el retado puede rechazar.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content=f"{self.rival.display_name} rechazó el desafío.", embed=None, view=None)

    @discord.ui.button(label="Cancelar", emoji="🏳️", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.retador.id:
            await interaction.response.send_message("Solo quien desafió puede cancelar.", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content="Desafío cancelado.", embed=None, view=None)


arena_group = app_commands.Group(name="arena", description="Combates PvP entre jugadores", guild_only=True)


@arena_group.command(name="desafiar", description="Desafía a otro jugador a un duelo en la arena")
@app_commands.describe(usuario="A quién quieres desafiar", apuesta="Dinero que se juegan (opcional)")
async def arena_desafiar(
    interaction: discord.Interaction, usuario: discord.Member,
    apuesta: app_commands.Range[int, 0, 1_000_000_000] = 0,
):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    if usuario.bot or usuario.id == interaction.user.id:
        await interaction.response.send_message("Elige a otro jugador para desafiar.", ephemeral=True)
        return
    fa = obtener_ficha(interaction.user.id, crear=True)
    fb = obtener_ficha(usuario.id)
    if not fa["raza_id"]:
        await interaction.response.send_message("Primero crea tu personaje con /raza.", ephemeral=True)
        return
    if fb is None or not fb["raza_id"]:
        await interaction.response.send_message(f"{usuario.display_name} todavía no tiene personaje.", ephemeral=True)
        return
    if interaction.user.id in BATALLAS_ACTIVAS or usuario.id in BATALLAS_ACTIVAS:
        await interaction.response.send_message("Alguno de los dos ya está en un combate.", ephemeral=True)
        return
    if apuesta and (fa["dinero"] < apuesta or fb["dinero"] < apuesta):
        await interaction.response.send_message("Alguno de los dos no tiene suficiente dinero para esa apuesta.", ephemeral=True)
        return
    vista = VistaDesafio(interaction.user, usuario, apuesta, interaction.guild_id)
    texto = f"⚔️ {usuario.mention}, **{interaction.user.display_name}** te desafía a un duelo en la arena."
    if apuesta:
        texto += f" Apuesta: {moneda(interaction.guild_id, apuesta)}."
    await interaction.response.send_message(texto, view=vista)
    vista.interaccion = interaction


@arena_group.command(name="ranking", description="Los mejores duelistas de la arena")
async def arena_ranking(interaction: discord.Interaction):
    filas = []
    for uid, f in cargar().items():
        p = f.get("pvp")
        if p and (p.get("victorias", 0) or p.get("derrotas", 0)):
            filas.append((int(uid), p.get("victorias", 0), p.get("derrotas", 0)))
    if not filas:
        await interaction.response.send_message("Todavía nadie ha peleado en la arena.", ephemeral=True)
        return
    filas.sort(key=lambda x: (-x[1], x[2]))
    medallas = ["🥇", "🥈", "🥉"]
    lineas = [
        f"{medallas[i] if i < 3 else f'**{i + 1}.**'} <@{uid}> — {v} victoria(s), {d} derrota(s)"
        for i, (uid, v, d) in enumerate(filas[:10])
    ]
    embed = discord.Embed(title="🏟️ Ranking de la Arena", description="\n".join(lineas), color=0xE67E22)
    await interaction.response.send_message(embed=embed)


bot.tree.add_command(arena_group)


# ============================================================
#  COMANDOS DE ADMINISTRADOR (solo el admin unico)
# ============================================================
CANT = app_commands.Range[int, -1_000_000_000, 1_000_000_000]


def _nombre_cambio(n):
    return f"+{n:,}" if n >= 0 else f"{n:,}"


@bot.tree.command(name="admin_dinero", description="[Admin] Da o quita dinero a un jugador")
@app_commands.describe(usuario="Jugador", cantidad="Cantidad (negativa para quitar)")
@app_commands.guild_only()
async def admin_dinero(interaction: discord.Interaction, usuario: discord.Member, cantidad: CANT):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    ficha["dinero"] = max(0, ficha["dinero"] + cantidad)
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(
        f'💰 {usuario.mention}: {_nombre_cambio(cantidad)}. Ahora tiene {moneda(interaction.guild_id, ficha["dinero"])}.', ephemeral=True
    )


@bot.tree.command(name="admin_ep", description="[Admin] Da o quita EP a un jugador")
@app_commands.describe(usuario="Jugador", cantidad="Cantidad (negativa para quitar)")
@app_commands.guild_only()
async def admin_ep(interaction: discord.Interaction, usuario: discord.Member, cantidad: CANT):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    ficha["ep"] = max(0, ficha["ep"] + cantidad)
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(f'⚡ {usuario.mention}: {_nombre_cambio(cantidad)} EP. Ahora tiene {ficha["ep"]:,}.', ephemeral=True)


@bot.tree.command(name="admin_exp", description="[Admin] Da o quita experiencia a un jugador")
@app_commands.describe(usuario="Jugador", cantidad="Cantidad (negativa para quitar)")
@app_commands.guild_only()
async def admin_exp(interaction: discord.Interaction, usuario: discord.Member, cantidad: CANT):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    ficha["exp"] = max(0, ficha["exp"] + cantidad)
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(f'📈 {usuario.mention}: {_nombre_cambio(cantidad)} EXP. Ahora tiene {ficha["exp"]:,}.', ephemeral=True)


@bot.tree.command(name="admin_material", description="[Admin] Da o quita materiales a un jugador")
@app_commands.describe(usuario="Jugador", nombre="Material (puedes escribir uno nuevo)", cantidad="Cantidad (negativa para quitar)")
@app_commands.guild_only()
async def admin_material(interaction: discord.Interaction, usuario: discord.Member, nombre: str, cantidad: CANT):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    nuevo = max(0, ficha["materiales"].get(nombre, 0) + cantidad)
    if nuevo:
        ficha["materiales"][nombre] = nuevo
    else:
        ficha["materiales"].pop(nombre, None)
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(f"📦 {usuario.mention}: {_nombre_cambio(cantidad)} {nombre}. Ahora tiene {nuevo:,}.", ephemeral=True)


@admin_material.autocomplete("nombre")
async def admin_material_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    return [app_commands.Choice(name=n, value=n) for n in TODOS_LOS_MATERIALES if current in n.lower()][:25]


@bot.tree.command(name="admin_objeto", description="[Admin] Da o quita objetos a un jugador")
@app_commands.describe(usuario="Jugador", nombre="Objeto (puedes escribir cualquier nombre)", cantidad="Cantidad (negativa para quitar)")
@app_commands.guild_only()
async def admin_objeto(interaction: discord.Interaction, usuario: discord.Member, nombre: str, cantidad: app_commands.Range[int, -100, 100]):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    if cantidad >= 0:
        ficha["objetos"].extend([nombre] * cantidad)
    else:
        for _ in range(-cantidad):
            if nombre in ficha["objetos"]:
                ficha["objetos"].remove(nombre)
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(f"🎒 {usuario.mention}: {_nombre_cambio(cantidad)} {nombre}.", ephemeral=True)


@admin_objeto.autocomplete("nombre")
async def admin_objeto_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    return [app_commands.Choice(name=n, value=n) for n in OBJETOS_CONOCIDOS if current in n.lower()][:25]


@bot.tree.command(name="admin_habilidad", description="[Admin] Da o quita una habilidad a un jugador")
@app_commands.describe(usuario="Jugador", habilidad="Habilidad", accion="Dar o quitar")
@app_commands.choices(accion=[
    app_commands.Choice(name="Dar", value="dar"),
    app_commands.Choice(name="Quitar", value="quitar"),
])
@app_commands.guild_only()
async def admin_habilidad(interaction: discord.Interaction, usuario: discord.Member, habilidad: str, accion: app_commands.Choice[str]):
    if not await exigir_admin(interaction):
        return
    if habilidad not in HABILIDADES:
        await interaction.response.send_message("Esa habilidad no existe. Elige una de la lista.", ephemeral=True)
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    nombre = HABILIDADES[habilidad]["nombre"]
    if accion.value == "dar":
        ficha["habilidades"].append(habilidad)
        msg = f"✨ {usuario.mention} recibió **{nombre}**."
    elif habilidad in ficha["habilidades"]:
        ficha["habilidades"].remove(habilidad)
        msg = f"✨ A {usuario.mention} se le quitó **{nombre}**."
    else:
        msg = f"{usuario.mention} no tiene **{nombre}**."
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(msg, ephemeral=True)


@admin_habilidad.autocomplete("habilidad")
async def admin_habilidad_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    return [
        app_commands.Choice(name=f'{RAREZA_EMOJI[h["rareza"]]} {h["nombre"]}', value=hid)
        for hid, h in HABILIDADES.items() if current in h["nombre"].lower()
    ][:25]


@bot.tree.command(name="admin_arma_genesis", description="[Admin] Entrega un arma Génesis a un jugador")
@app_commands.describe(usuario="Jugador", arma="Arma Génesis")
@app_commands.choices(arma=[app_commands.Choice(name=a["nombre"], value=k) for k, a in ARMAS_GENESIS.items()])
@app_commands.guild_only()
async def admin_arma_genesis(interaction: discord.Interaction, usuario: discord.Member, arma: app_commands.Choice[str]):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    datos = ARMAS_GENESIS[arma.value]
    ficha["forjados"][nuevo_id_objeto()] = {"nombre": datos["nombre"], "tipo": "arma", "rareza": "genesis"}
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(
        f'🌈 {usuario.mention} recibió el arma Génesis **{datos["nombre"]}**. {datos["descripcion"]}', ephemeral=True
    )


@bot.tree.command(name="admin_pocion", description="[Admin] Da pociones a un jugador")
@app_commands.describe(usuario="Jugador", tipo="Tipo de poción", nivel="Potencia", cantidad="Cuántas")
@app_commands.choices(
    tipo=[app_commands.Choice(name=NOMBRES_TIPO_POCION[t], value=t) for t in TIPOS_POCION],
    nivel=[app_commands.Choice(name=f"{n}%", value=n) for n in PRECIOS_POCION],
)
@app_commands.guild_only()
async def admin_pocion(
    interaction: discord.Interaction, usuario: discord.Member,
    tipo: app_commands.Choice[str], nivel: app_commands.Choice[int],
    cantidad: app_commands.Range[int, 1, 99] = 1,
):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    clave = clave_pocion(tipo.value, nivel.value)
    ficha["pociones"][clave] = ficha["pociones"].get(clave, 0) + cantidad
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(
        f"🧪 {usuario.mention} recibió {cantidad}x {nombre_pocion(tipo.value, nivel.value)}.", ephemeral=True
    )


@bot.tree.command(name="admin_raza", description="[Admin] Cambia la raza (y etapa) de un jugador")
@app_commands.describe(usuario="Jugador", raza="Raza", etapa="Etapa (0 = base)")
@app_commands.guild_only()
async def admin_raza(interaction: discord.Interaction, usuario: discord.Member, raza: str, etapa: app_commands.Range[int, 0, 10] = 0):
    if not await exigir_admin(interaction):
        return
    if raza not in RAZAS:
        await interaction.response.send_message("Esa raza no existe. Elige una de la lista.", ephemeral=True)
        return
    etapa = min(etapa, len(RAZAS[raza]["evo"]))
    ficha = obtener_ficha(usuario.id, crear=True)
    ficha["raza_id"] = raza
    ficha["etapa"] = etapa
    ficha["raza"] = nombre_etapa(raza, etapa)
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(f'🧬 {usuario.mention} ahora es **{ficha["raza"]}**.', ephemeral=True)


@admin_raza.autocomplete("raza")
async def admin_raza_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    return [app_commands.Choice(name=r["nombre"], value=rid) for rid, r in RAZAS.items() if current in r["nombre"].lower()][:25]


@bot.tree.command(name="admin_mision_completar", description="[Admin] Cierra la misión del gremio de un jugador y le da la recompensa")
@app_commands.describe(usuario="Jugador")
@app_commands.guild_only()
async def admin_mision_completar(interaction: discord.Interaction, usuario: discord.Member):
    if not await exigir_admin(interaction):
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    g = gremio_estado(ficha)
    en_curso = g["en_progreso"]
    if not en_curso:
        guardar_ficha(usuario.id, ficha)
        await interaction.response.send_message(f"{usuario.display_name} no tiene ninguna misión en curso.", ephemeral=True)
        return
    rango = en_curso["rango"]
    dinero_r, exp_r = RECOMPENSAS_RANGO[rango]
    ficha["dinero"] += dinero_r
    ficha["exp"] += exp_r
    g["completadas_hoy"].append(rango)
    g["en_progreso"] = None
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(
        f"🏹 Misión de rango {rango} completada por {usuario.mention}: "
        f"+{moneda(interaction.guild_id, dinero_r)} y +{exp_r:,} EXP."
    )


@bot.tree.command(name="admin_reset", description="[Admin] Borra por completo el personaje de un jugador")
@app_commands.describe(usuario="Jugador", confirmar="Escribe BORRAR para confirmar")
@app_commands.guild_only()
async def admin_reset(interaction: discord.Interaction, usuario: discord.Member, confirmar: str):
    if not await exigir_admin(interaction):
        return
    if confirmar != "BORRAR":
        await interaction.response.send_message("Para confirmar escribe exactamente BORRAR.", ephemeral=True)
        return
    ficha = obtener_ficha(usuario.id, crear=True)
    ficha.clear()
    ficha.update(copy.deepcopy(FICHA_BASE))
    guardar_ficha(usuario.id, ficha)
    await interaction.response.send_message(f"🗑️ El personaje de {usuario.mention} fue reiniciado.", ephemeral=True)


@bot.tree.command(name="admin_moneda", description="[Admin] Cambia el emoji de la moneda del servidor")
@app_commands.describe(emoji="Nuevo emoji")
@app_commands.guild_only()
async def admin_moneda(interaction: discord.Interaction, emoji: str):
    if not await exigir_admin(interaction):
        return
    conf = config_guild(interaction.guild_id)
    conf["moneda_emoji"] = emoji[:50]
    guardar_config_guild(interaction.guild_id, conf)
    await interaction.response.send_message(f"Moneda cambiada: {moneda(interaction.guild_id, 1000)}", ephemeral=True)


@bot.tree.command(name="admin_rol_jugador", description="[Admin] Limita el bot a ciertos roles (si no hay ninguno, juega todo el mundo)")
@app_commands.describe(rol="Rol", accion="Qué hacer con ese rol")
@app_commands.choices(accion=[
    app_commands.Choice(name="Permitir jugar", value="agregar"),
    app_commands.Choice(name="Quitar permiso", value="quitar"),
    app_commands.Choice(name="Quitar todos (todos pueden jugar)", value="limpiar"),
])
@app_commands.guild_only()
async def admin_rol_jugador(interaction: discord.Interaction, accion: app_commands.Choice[str], rol: discord.Role = None):
    if not await exigir_admin(interaction):
        return
    conf = config_guild(interaction.guild_id)
    if accion.value == "limpiar":
        conf["jugador_roles"] = []
    else:
        if rol is None:
            await interaction.response.send_message("Elige también el rol.", ephemeral=True)
            return
        if accion.value == "agregar" and rol.id not in conf["jugador_roles"]:
            conf["jugador_roles"].append(rol.id)
        elif accion.value == "quitar" and rol.id in conf["jugador_roles"]:
            conf["jugador_roles"].remove(rol.id)
    guardar_config_guild(interaction.guild_id, conf)
    roles = ", ".join(f"<@&{r}>" for r in conf["jugador_roles"]) or "todos pueden jugar"
    await interaction.response.send_message(f"Roles de jugador: {roles}", ephemeral=True)


# ============================================================
#  /configuracion  (panel del dueño del servidor)
# ============================================================
def _menciones(ids, rol=False):
    if not ids:
        return "*Nadie todavía*"
    pref = "@&" if rol else "@"
    return "\n".join(f"<{pref}{i}>" for i in ids)[:1000]


def _alternar(lista, i):
    """Si ya estaba en la lista lo quita; si no, lo agrega."""
    if i in lista:
        lista.remove(i)
    else:
        lista.append(i)


def embed_config(guild):
    conf = config_guild(guild.id)
    embed = discord.Embed(
        title="⚙️ Panel de Configuración",
        description=(
            f"Bienvenido al panel de **{guild.name}**.\n"
            "Aquí decides **quién puede usar los comandos de admin** y cómo funciona el bot.\n"
            "▫️ Los menús *añaden o quitan*: elige a alguien que ya está y se le quita."
        ),
        color=0xC9A227,
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Dueño (siempre es admin)", value=f"<@{guild.owner_id}>", inline=False)
    embed.add_field(name="🛡️ Admins (personas)", value=_menciones(conf.get("admin_usuarios", [])), inline=True)
    embed.add_field(name="🎖️ Admins (roles)", value=_menciones(conf.get("admin_roles", []), rol=True), inline=True)
    jugadores = conf.get("jugador_roles", [])
    embed.add_field(
        name="🎮 Roles que pueden jugar",
        value=_menciones(jugadores, rol=True) if jugadores else "✅ Todo el mundo puede jugar",
        inline=False,
    )
    embed.add_field(name="🪙 Moneda", value=f'{conf["moneda_emoji"]}  (ejemplo: {moneda(guild.id, 1000)})', inline=True)
    embed.add_field(name="🧙 Personajes creados", value=f"{sum(1 for f in cargar().values() if f.get('raza_id')):,}", inline=True)
    embed.set_footer(text="🔒 Solo el dueño del servidor puede cambiar esto")
    return embed


class ModalMoneda(discord.ui.Modal):
    def __init__(self, vista):
        super().__init__(title="Moneda del servidor")
        self.vista = vista
        self.campo = discord.ui.TextInput(label="Emoji de la moneda", placeholder="🪙", max_length=50)
        self.add_item(self.campo)

    async def on_submit(self, interaction: discord.Interaction):
        conf = config_guild(interaction.guild_id)
        conf["moneda_emoji"] = self.campo.value.strip() or "🪙"
        guardar_config_guild(interaction.guild_id, conf)
        await interaction.response.edit_message(embed=embed_config(interaction.guild), view=self.vista)


class VistaConfig(VistaBase):
    def __init__(self, dueno_id):
        super().__init__(dueno_id, timeout=600)

    async def _refrescar(self, interaction):
        await interaction.response.edit_message(embed=embed_config(interaction.guild), view=self)

    @discord.ui.select(
        cls=discord.ui.UserSelect, row=0, min_values=1, max_values=10,
        placeholder="👤 Añadir / quitar admins (personas)",
    )
    async def sel_usuarios(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        conf = config_guild(interaction.guild_id)
        lista = conf.setdefault("admin_usuarios", [])
        for u in select.values:
            if u.bot or u.id == interaction.guild.owner_id:
                continue
            _alternar(lista, u.id)
        guardar_config_guild(interaction.guild_id, conf)
        await self._refrescar(interaction)

    @discord.ui.select(
        cls=discord.ui.RoleSelect, row=1, min_values=1, max_values=10,
        placeholder="🎖️ Añadir / quitar roles admin",
    )
    async def sel_roles_admin(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        conf = config_guild(interaction.guild_id)
        for r in select.values:
            if r.is_default():
                continue
            _alternar(conf["admin_roles"], r.id)
        guardar_config_guild(interaction.guild_id, conf)
        await self._refrescar(interaction)

    @discord.ui.select(
        cls=discord.ui.RoleSelect, row=2, min_values=1, max_values=10,
        placeholder="🎮 Añadir / quitar roles que pueden jugar",
    )
    async def sel_roles_jugador(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        conf = config_guild(interaction.guild_id)
        for r in select.values:
            if r.is_default():
                continue
            _alternar(conf["jugador_roles"], r.id)
        guardar_config_guild(interaction.guild_id, conf)
        await self._refrescar(interaction)

    @discord.ui.button(label="Quitar admins", emoji="🧹", style=discord.ButtonStyle.secondary, row=3)
    async def limpiar_admins(self, interaction: discord.Interaction, button: discord.ui.Button):
        conf = config_guild(interaction.guild_id)
        conf["admin_usuarios"] = []
        conf["admin_roles"] = []
        guardar_config_guild(interaction.guild_id, conf)
        await self._refrescar(interaction)

    @discord.ui.button(label="Todos pueden jugar", emoji="🌍", style=discord.ButtonStyle.secondary, row=3)
    async def limpiar_jugadores(self, interaction: discord.Interaction, button: discord.ui.Button):
        conf = config_guild(interaction.guild_id)
        conf["jugador_roles"] = []
        guardar_config_guild(interaction.guild_id, conf)
        await self._refrescar(interaction)

    @discord.ui.button(label="Moneda", emoji="🪙", style=discord.ButtonStyle.primary, row=3)
    async def cambiar_moneda(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalMoneda(self))

    @discord.ui.button(label="Actualizar", emoji="🔄", style=discord.ButtonStyle.success, row=3)
    async def actualizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refrescar(interaction)


@bot.tree.command(name="configuracion", description="Panel del dueño: elige quién puede usar los comandos de admin")
@app_commands.guild_only()
async def configuracion(interaction: discord.Interaction):
    if not es_dueno_servidor(interaction):
        await interaction.response.send_message("👑 Solo el dueño del servidor puede abrir este panel.", ephemeral=True)
        return
    await interaction.response.send_message(
        embed=embed_config(interaction.guild), view=VistaConfig(interaction.user.id), ephemeral=True
    )


# ============================================================
#  EXTRAS DIVERTIDOS: /diario /entrenar /pagar /top
# ============================================================
@bot.tree.command(name="diario", description="Reclama tu recompensa diaria (con racha: cada día seguido paga más)")
@app_commands.guild_only()
async def diario(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if not ficha["raza_id"]:
        await interaction.response.send_message("Primero crea tu personaje con /raza.", ephemeral=True)
        return
    d = ficha.setdefault("diario", {"fecha": "", "racha": 0})
    hoy = fecha_hoy()
    if d["fecha"] == hoy:
        await interaction.response.send_message("Ya reclamaste tu recompensa de hoy. Vuelve mañana (UTC).", ephemeral=True)
        return
    ayer = (date.fromisoformat(hoy) - timedelta(days=1)).isoformat()
    d["racha"] = d["racha"] + 1 if d["fecha"] == ayer else 1
    d["fecha"] = hoy
    factor = 1 + rango_index(rango_por_ep(ficha["ep"]))
    dinero = (100 + 50 * min(d["racha"], 10)) * factor
    ficha["dinero"] += dinero
    extras = []
    if random.random() < 0.25:
        clave = clave_pocion("vida", 25)
        ficha["pociones"][clave] = ficha["pociones"].get(clave, 0) + 1
        extras.append(f'🧪 ¡Bonus! Encontraste una {nombre_pocion("vida", 25)}.')
    if d["racha"] % 7 == 0:
        hid = tirar_habilidad(PESOS_ROLL)
        ficha["habilidades"].append(hid)
        h = HABILIDADES[hid]
        extras.append(f'🎁 ¡Racha de {d["racha"]} días! Habilidad gratis: {RAREZA_EMOJI[h["rareza"]]} **{h["nombre"]}**.')
    guardar_ficha(interaction.user.id, ficha)
    embed = discord.Embed(
        title="🎁 Recompensa diaria",
        description=f'Recibes **{moneda(interaction.guild_id, dinero)}**.\n🔥 Racha: **{d["racha"]}** día(s)'
                    + ("\n" + "\n".join(extras) if extras else ""),
        color=0xF1C40F,
    )
    embed.set_footer(text="Entra todos los días: la racha sube el premio hasta el día 10, y cada 7 días hay habilidad gratis.")
    await interaction.response.send_message(embed=embed)


ENTRENAMIENTOS = [
    "Golpeas un muñeco de paja hasta el amanecer.",
    "Meditas bajo una cascada helada.",
    "Corres con rocas atadas a la espalda por el bosque de Jura.",
    "Practicas combate con un instructor veterano del gremio.",
    "Esquivas flechas lanzadas por reclutas del gremio.",
    "Levantas troncos en el patio de entrenamiento de Lubelius.",
]
COOLDOWN_ENTRENAR = 30 * 60


@bot.tree.command(name="entrenar", description="Entrena un rato para ganar EXP y EP (cada 30 minutos)")
@app_commands.guild_only()
async def entrenar(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if not ficha["raza_id"]:
        await interaction.response.send_message("Primero crea tu personaje con /raza.", ephemeral=True)
        return
    espera = int(ficha.get("entrenar_hasta", 0) - time.time())
    if espera > 0:
        await interaction.response.send_message(f"Estás cansado. Podrás entrenar en {texto_tiempo(espera)}.", ephemeral=True)
        return
    exp = random.randint(20, 50) * (1 + ficha["etapa"])
    critico = random.random() < 0.10
    if critico:
        exp *= 3
    ep = max(1, exp // 4)
    ficha["exp"] += exp
    ficha["ep"] += ep
    ficha["entrenar_hasta"] = time.time() + COOLDOWN_ENTRENAR
    guardar_ficha(interaction.user.id, ficha)
    texto = random.choice(ENTRENAMIENTOS)
    if critico:
        texto += "\n💥 ¡Entrenamiento perfecto! Ganas el triple."
    await interaction.response.send_message(f"🏋️ {texto}\n📈 **+{exp:,} EXP** · ⚡ **+{ep:,} EP**")


@bot.tree.command(name="pagar", description="Regala dinero a otro jugador")
@app_commands.describe(usuario="Quién recibe el dinero", cantidad="Cuánto")
@app_commands.guild_only()
async def pagar(interaction: discord.Interaction, usuario: discord.Member, cantidad: app_commands.Range[int, 1, 1_000_000_000]):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    if usuario.bot or usuario.id == interaction.user.id:
        await interaction.response.send_message("Elige a otro jugador.", ephemeral=True)
        return
    emisor = obtener_ficha(interaction.user.id, crear=True)
    receptor = obtener_ficha(usuario.id)
    if receptor is None or not receptor["raza_id"]:
        await interaction.response.send_message(f"{usuario.display_name} todavía no tiene personaje.", ephemeral=True)
        return
    if emisor["dinero"] < cantidad:
        await interaction.response.send_message(
            f'No te alcanza: tienes {moneda(interaction.guild_id, emisor["dinero"])}.', ephemeral=True
        )
        return
    emisor["dinero"] -= cantidad
    receptor["dinero"] += cantidad
    guardar_ficha(interaction.user.id, emisor)
    guardar_ficha(usuario.id, receptor)
    await interaction.response.send_message(
        f"💸 {interaction.user.mention} le dio **{moneda(interaction.guild_id, cantidad)}** a {usuario.mention}."
    )


@bot.tree.command(name="top", description="Los mejores jugadores del bot")
@app_commands.describe(categoria="Qué ranking quieres ver")
@app_commands.choices(categoria=[
    app_commands.Choice(name="⚡ Más EP", value="ep"),
    app_commands.Choice(name="💰 Más dinero", value="dinero"),
    app_commands.Choice(name="🏟️ Más victorias PvP", value="victorias"),
])
@app_commands.guild_only()
async def top(interaction: discord.Interaction, categoria: app_commands.Choice[str]):
    filas = []
    for uid, f in cargar().items():
        if not f.get("raza_id"):
            continue
        if categoria.value == "victorias":
            valor = f.get("pvp", {}).get("victorias", 0)
        else:
            valor = f.get(categoria.value, 0)
        if valor > 0:
            filas.append((int(uid), valor, f.get("raza", "?")))
    if not filas:
        await interaction.response.send_message("Todavía no hay nadie en este ranking.", ephemeral=True)
        return
    filas.sort(key=lambda x: -x[1])
    medallas = ["🥇", "🥈", "🥉"]
    lineas = [
        f"{medallas[i] if i < 3 else f'**{i + 1}.**'} <@{uid}> · {raza_txt} — **{valor:,}**"
        for i, (uid, valor, raza_txt) in enumerate(filas[:10])
    ]
    embed = discord.Embed(title=f"🏆 Top: {categoria.name}", description="\n".join(lineas), color=0xF1C40F)
    await interaction.response.send_message(embed=embed)


# ============================================================
#  ARRANQUE
# ============================================================
if __name__ == "__main__":
    bot.run(TOKEN)
