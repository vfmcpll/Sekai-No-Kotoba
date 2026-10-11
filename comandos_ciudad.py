import random
import time
import discord
from discord import app_commands

from nucleo import *


POR_PAGINA = 25   # Discord solo deja 25 opciones por menu desplegable


def pagina_de(items, pagina, por_pagina=POR_PAGINA):
    """Devuelve (items de la pagina, pagina real, total de paginas)."""
    total = max(1, -(-len(items) // por_pagina))
    pagina = max(0, min(pagina, total - 1))
    return items[pagina * por_pagina:(pagina + 1) * por_pagina], pagina, total


class BotonPagina(discord.ui.Button):
    def __init__(self, delta, deshabilitado):
        super().__init__(
            emoji="◀️" if delta < 0 else "▶️", style=discord.ButtonStyle.secondary,
            disabled=deshabilitado,
        )
        self.delta = delta

    async def callback(self, interaction: discord.Interaction):
        vista = self.view.con_pagina(self.view.pagina + self.delta)
        await interaction.response.edit_message(view=vista)


FRASES_LUBELIUS = [
    "Las campanas de la Catedral repican a lo lejos.",
    "Un grupo de Crusaders patrulla la plaza principal.",
    "El aroma a pan recién horneado sale de las panaderías cercanas.",
    "Peregrinos de todo el continente hacen fila para entrar a la Catedral.",
    "Un trovador canta viejas historias de héroes junto a la fuente.",
    "Los comerciantes anuncian a gritos las ofertas del día.",
    "Un carruaje real cruza la plaza escoltado por soldados.",
    "El sol se refleja en los vitrales de la Catedral de Occidente.",
]


def embed_ciudad(ficha, guild_id):
    g = gremio_estado(ficha)
    embed = discord.Embed(
        title="🏙️ Lubelius",
        description=(
            "La ciudad santa de Occidente, sede de la Iglesia y de sus Crusaders.\n"
            f"*{random.choice(FRASES_LUBELIUS)}*"
        ),
        color=0xC9A227,
    )
    embed.add_field(name="💰 Dinero", value=moneda(guild_id, ficha["dinero"]), inline=True)
    embed.add_field(name="🎖️ Rango", value=rango_por_ep(ficha["ep"]), inline=True)
    descanso = "✅ Descansado" if ficha["descansado"] else "❌ Sin descansar"
    embed.add_field(name="🛌 Posada", value=descanso, inline=True)

    if g["en_progreso"]:
        estado_gremio = "🕓 Misión en curso"
    elif len(g["completadas_hoy"]) >= len(RANGOS_MISION):
        estado_gremio = "✅ Todo completado hoy"
    else:
        estado_gremio = f'{len(g["completadas_hoy"])} completada(s) hoy'
    embed.add_field(name="🏹 Gremio", value=estado_gremio, inline=True)

    embed.set_footer(text="Elige a dónde ir con los botones de abajo.")
    return embed


class VistaCiudad(VistaBase):
    def __init__(self, dueno_id, guild_id):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Tienda", emoji="🛒", style=discord.ButtonStyle.primary, row=0)
    async def tienda(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaTienda(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_tienda(ficha, self.guild_id), view=vista)

    @discord.ui.button(label="Gremio", emoji="🏹", style=discord.ButtonStyle.primary, row=0)
    async def gremio(self, interaction: discord.Interaction, button: discord.ui.Button):
        vista = VistaGremio(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=vista.crear_embed(), view=vista)

    @discord.ui.button(label="Casino", emoji="🎰", style=discord.ButtonStyle.primary, row=0)
    async def casino(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaCasino(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_casino(ficha, self.guild_id), view=vista)

    @discord.ui.button(label="Posada", emoji="🛌", style=discord.ButtonStyle.secondary, row=1)
    async def posada(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        hoy = fecha_hoy()
        if ficha["descanso_fecha"] == hoy:
            await interaction.response.send_message(
                "Ya descansaste hoy. El posadero te guiña el ojo: vuelve mañana.", ephemeral=True
            )
            return
        ficha["descanso_fecha"] = hoy
        ficha["descansado"] = True
        guardar_ficha(self.dueno_id, ficha)
        vista = VistaCiudad(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(
            content="🛌 Duermes una noche tranquila. Tu próximo combate empezará con algo más de fuerza.",
            embed=embed_ciudad(ficha, self.guild_id), view=vista,
        )

    @discord.ui.button(label="Forja", emoji="🔨", style=discord.ButtonStyle.secondary, row=1)
    async def forja(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaForja(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_forja(ficha, self.guild_id), view=vista)


# ---------------- Casino ----------------
def embed_casino(ficha, guild_id):
    embed = discord.Embed(
        title="🎰 Casino de Lubelius",
        description="Juegos de toda la vida, nada de máquinas modernas: dados, una moneda y piedra-papel-tijera contra la casa.",
        color=0x7D3C98,
    )
    embed.add_field(name="💰 Tu dinero", value=moneda(guild_id, ficha["dinero"]), inline=False)
    embed.set_footer(text="Ganar paga el doble de tu apuesta; empatar te la devuelve; perder la pierdes.")
    return embed


def jugar_dados(apuesta):
    tuyo = random.randint(1, 6) + random.randint(1, 6)
    casa = random.randint(1, 6) + random.randint(1, 6)
    if tuyo > casa:
        return f"🎲 Tiraste **{tuyo}** contra **{casa}** de la casa. ¡Ganaste!", apuesta
    if tuyo == casa:
        return f"🎲 Empate a **{tuyo}**. Recuperas tu apuesta.", 0
    return f"🎲 Tiraste **{tuyo}** contra **{casa}** de la casa. Perdiste.", -apuesta


def jugar_moneda(apuesta):
    if random.random() < 0.5:
        return "🪙 La moneda cae de cara. ¡Ganaste!", apuesta
    return "🪙 La moneda cae de cruz. Perdiste.", -apuesta


def jugar_piedra_papel_tijera(apuesta, eleccion):
    opciones = ["piedra", "papel", "tijera"]
    casa = random.choice(opciones)
    if eleccion == casa:
        return f"✊ Los dos eligieron **{casa}**. Empate, recuperas tu apuesta.", 0
    gana_a = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}
    if gana_a[eleccion] == casa:
        return f"✊ Elegiste **{eleccion}**, la casa **{casa}**. ¡Ganaste!", apuesta
    return f"✊ Elegiste **{eleccion}**, la casa **{casa}**. Perdiste.", -apuesta


class ModalApuestaCasino(discord.ui.Modal):
    def __init__(self, dueno_id, guild_id, juego):
        super().__init__(title=f"Apostar: {juego}")
        self.dueno_id = dueno_id
        self.guild_id = guild_id
        self.juego = juego
        self.apuesta_input = discord.ui.TextInput(label="¿Cuánto quieres apostar?", placeholder="Ej: 100")
        self.add_item(self.apuesta_input)
        if juego == "rpt":
            self.eleccion_input = discord.ui.TextInput(
                label="Piedra, papel o tijera", placeholder="piedra / papel / tijera"
            )
            self.add_item(self.eleccion_input)

    async def on_submit(self, interaction: discord.Interaction):
        texto = self.apuesta_input.value.strip()
        if not texto.isdigit() or int(texto) <= 0:
            await interaction.response.send_message("Escribe un número entero positivo.", ephemeral=True)
            return
        apuesta = int(texto)
        ficha = obtener_ficha(self.dueno_id, crear=True)
        if ficha["dinero"] < apuesta:
            await interaction.response.send_message(
                f"No tienes esa cantidad. Tienes {moneda(self.guild_id, ficha['dinero'])}.", ephemeral=True
            )
            return

        if self.juego == "dados":
            resultado, cambio = jugar_dados(apuesta)
        elif self.juego == "moneda":
            resultado, cambio = jugar_moneda(apuesta)
        else:
            eleccion = self.eleccion_input.value.strip().lower()
            if eleccion not in ("piedra", "papel", "tijera"):
                await interaction.response.send_message("Escribe piedra, papel o tijera.", ephemeral=True)
                return
            resultado, cambio = jugar_piedra_papel_tijera(apuesta, eleccion)

        ficha["dinero"] += cambio
        guardar_ficha(self.dueno_id, ficha)
        vista = VistaCasino(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(
            content=resultado, embed=embed_casino(ficha, self.guild_id), view=vista,
        )


class VistaCasino(VistaBase):
    def __init__(self, dueno_id, guild_id):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Dados", emoji="🎲", style=discord.ButtonStyle.success)
    async def dados(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalApuestaCasino(self.dueno_id, self.guild_id, "dados"))

    @discord.ui.button(label="Cara o Cruz", emoji="🪙", style=discord.ButtonStyle.success)
    async def moneda_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalApuestaCasino(self.dueno_id, self.guild_id, "moneda"))

    @discord.ui.button(label="Piedra, Papel o Tijera", emoji="✊", style=discord.ButtonStyle.success)
    async def rpt_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModalApuestaCasino(self.dueno_id, self.guild_id, "rpt"))

    @discord.ui.button(label="Volver a la ciudad", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaCiudad(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_ciudad(ficha, self.guild_id), view=vista)


# ---------------- Forja ----------------
def embed_forja(ficha, guild_id):
    embed = discord.Embed(
        title="🔨 Forja de Lubelius",
        description=(
            "Entrega materiales al herrero para forjar un arma o una armadura. "
            "Cuanto mejor el material, mejor puede salir la pieza — pero dar muy poco "
            "o demasiado puede arruinar la forja."
        ),
        color=0x8B5A2B,
    )
    fp = ficha["forja_en_progreso"]
    if fp:
        restante = int(fp["termina"] - time.time())
        if restante > 0:
            minutos, segundos = divmod(max(restante, 0), 60)
            estado = (
                f'🕓 En proceso: {fp["tipo"].capitalize()} {NOMBRE_RAREZA_FORJA[fp["rareza"]]} '
                f"— lista en {minutos}m {segundos}s."
            )
        else:
            estado = "✅ ¡Tu forja está lista! Usa el botón Recoger."
    else:
        estado = "El yunque está libre. Puedes empezar una forja nueva."
    embed.add_field(name="Estado", value=estado, inline=False)

    equipo = ficha["equipado"]
    arma_txt = "Ninguna"
    if equipo["arma"] and equipo["arma"] in ficha["forjados"]:
        it = ficha["forjados"][equipo["arma"]]
        arma_txt = f'{EMOJI_RAREZA_FORJA[it["rareza"]]} {it["nombre"]} ({NOMBRE_RAREZA_FORJA[it["rareza"]]})'
    armadura_txt = "Ninguna"
    if equipo["armadura"] and equipo["armadura"] in ficha["forjados"]:
        it = ficha["forjados"][equipo["armadura"]]
        armadura_txt = f'{EMOJI_RAREZA_FORJA[it["rareza"]]} {it["nombre"]} ({NOMBRE_RAREZA_FORJA[it["rareza"]]})'
    embed.add_field(name="⚔️ Arma equipada", value=arma_txt, inline=True)
    embed.add_field(name="🛡️ Armadura equipada", value=armadura_txt, inline=True)
    embed.set_footer(text="Usa /equipar para cambiar tu arma o armadura.")
    return embed


class ModalNombreForja(discord.ui.Modal):
    def __init__(self, dueno_id, guild_id):
        super().__init__(title="Nombra tu creación")
        self.dueno_id = dueno_id
        self.guild_id = guild_id
        self.nombre_input = discord.ui.TextInput(
            label="¿Qué nombre le pones?", placeholder="Ej: Colmillo del Alba", max_length=60
        )
        self.add_item(self.nombre_input)

    async def on_submit(self, interaction: discord.Interaction):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        fp = ficha["forja_en_progreso"]
        if not fp or not fp["exito"]:
            await interaction.response.send_message("No hay nada que nombrar.", ephemeral=True)
            return
        nombre = self.nombre_input.value.strip() or "Creación sin nombre"
        item_id = nuevo_id_objeto()
        ficha["forjados"][item_id] = {"nombre": nombre, "tipo": fp["tipo"], "rareza": fp["rareza"]}
        ficha["forja_en_progreso"] = None
        guardar_ficha(self.dueno_id, ficha)
        emoji = EMOJI_RAREZA_FORJA[fp["rareza"]]
        await interaction.response.edit_message(
            content=f'🎉 ¡Forja exitosa! Creaste {emoji} **{nombre}** '
                    f'({fp["tipo"]}, rareza {NOMBRE_RAREZA_FORJA[fp["rareza"]]}).',
            embed=embed_forja(ficha, self.guild_id), view=VistaForja(self.dueno_id, self.guild_id),
        )


class ModalCantidadForja(discord.ui.Modal):
    def __init__(self, dueno_id, guild_id, tipo, material, rareza):
        super().__init__(title=f"Forjar {NOMBRE_RAREZA_FORJA[rareza]}")
        self.dueno_id = dueno_id
        self.guild_id = guild_id
        self.tipo = tipo
        self.material = material
        self.rareza = rareza
        ideal = CANTIDAD_IDEAL_FORJA[rareza]
        self.cantidad_input = discord.ui.TextInput(
            label=f"¿Cuántos {material[:30]} usar? (ideal {ideal})", placeholder=str(ideal)
        )
        self.add_item(self.cantidad_input)

    async def on_submit(self, interaction: discord.Interaction):
        texto = self.cantidad_input.value.strip()
        if not texto.isdigit() or int(texto) <= 0:
            await interaction.response.send_message("Escribe un número entero positivo.", ephemeral=True)
            return
        cantidad = int(texto)
        ficha = obtener_ficha(self.dueno_id, crear=True)
        if ficha["forja_en_progreso"]:
            await interaction.response.send_message("Ya tienes una forja en curso.", ephemeral=True)
            return
        disponible = ficha["materiales"].get(self.material, 0)
        if disponible < cantidad:
            await interaction.response.send_message(
                f"No tienes suficiente: tienes {disponible}x {self.material}.", ephemeral=True
            )
            return

        ficha["materiales"][self.material] -= cantidad
        if ficha["materiales"][self.material] <= 0:
            del ficha["materiales"][self.material]

        ideal = CANTIDAD_IDEAL_FORJA[self.rareza]
        exito = random.random() < probabilidad_exito_forja(cantidad, ideal)
        minutos = TIEMPO_FORJA_MINUTOS[self.rareza]
        ficha["forja_en_progreso"] = {
            "tipo": self.tipo, "rareza": self.rareza, "termina": time.time() + minutos * 60,
            "exito": exito, "material": self.material, "cantidad": cantidad,
        }
        guardar_ficha(self.dueno_id, ficha)

        vista = VistaForja(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(
            content=f"🔥 Pusiste {cantidad}x {self.material} en el yunque para forjar "
                    f"{NOMBRE_RAREZA_FORJA[self.rareza]}. Estará lista en {minutos} minutos.",
            embed=embed_forja(ficha, self.guild_id), view=vista,
        )


class SelectRarezaForja(discord.ui.Select):
    def __init__(self, tipo, material, rareza_material):
        tope = ORDEN_RAREZA_FORJA[rareza_material]
        opciones = [
            discord.SelectOption(
                label=NOMBRE_RAREZA_FORJA[r], value=r,
                description=f"Ideal: {CANTIDAD_IDEAL_FORJA[r]}x {material}"[:100],
                emoji=EMOJI_RAREZA_FORJA[r],
            )
            for r in ("comun", "extra", "unica", "definitiva") if ORDEN_RAREZA_FORJA[r] <= tope
        ]
        super().__init__(placeholder="Elige la rareza objetivo", options=opciones)
        self.tipo = tipo
        self.material = material

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            ModalCantidadForja(self.view.dueno_id, self.view.guild_id, self.tipo, self.material, self.values[0])
        )


class VistaForjaRareza(VistaBase):
    def __init__(self, dueno_id, guild_id, tipo, material, rareza_material):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id
        self.add_item(SelectRarezaForja(tipo, material, rareza_material))


class SelectMaterialForja(discord.ui.Select):
    def __init__(self, tipo, ficha, pagina=0):
        items = sorted(
            ficha["materiales"].items(),
            key=lambda kv: (-ORDEN_RAREZA_FORJA.get(RAREZA_MATERIALES.get(kv[0], "comun"), 0), kv[0]),
        )
        items, self.pagina, self.total = pagina_de(items, pagina)
        opciones = []
        for nombre, cantidad in items:
            rareza = RAREZA_MATERIALES.get(nombre, "comun")
            opciones.append(discord.SelectOption(
                label=f"{nombre} x{cantidad}"[:100], value=nombre,
                description=f"Rareza: {NOMBRE_RAREZA_FORJA[rareza]}", emoji=EMOJI_RAREZA_FORJA[rareza],
            ))
        placeholder = "Elige un material" + (f" ({self.pagina + 1}/{self.total})" if self.total > 1 else "")
        super().__init__(placeholder=placeholder, options=opciones)
        self.tipo = tipo

    async def callback(self, interaction: discord.Interaction):
        nombre = self.values[0]
        rareza_material = RAREZA_MATERIALES.get(nombre, "comun")
        vista = VistaForjaRareza(self.view.dueno_id, self.view.guild_id, self.tipo, nombre, rareza_material)
        await interaction.response.edit_message(
            content=f'Material elegido: **{nombre}** (rareza {NOMBRE_RAREZA_FORJA[rareza_material]}).\n'
                    "¿Qué rareza de pieza quieres intentar?",
            view=vista,
        )


class VistaForjaMaterial(VistaBase):
    def __init__(self, dueno_id, guild_id, tipo, ficha, pagina=0):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id
        self.tipo = tipo
        select = SelectMaterialForja(tipo, ficha, pagina)
        self.pagina, self.total = select.pagina, select.total
        self.add_item(select)
        if self.total > 1:
            self.add_item(BotonPagina(-1, self.pagina == 0))
            self.add_item(BotonPagina(+1, self.pagina >= self.total - 1))

    def con_pagina(self, pagina):
        return VistaForjaMaterial(self.dueno_id, self.guild_id, self.tipo, obtener_ficha(self.dueno_id, crear=True), pagina)


class VistaForjaTipo(VistaBase):
    def __init__(self, dueno_id, guild_id):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Arma", emoji="⚔️", style=discord.ButtonStyle.primary)
    async def arma(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaForjaMaterial(self.dueno_id, self.guild_id, "arma", ficha)
        await interaction.response.edit_message(content="Elige el material a usar:", view=vista)

    @discord.ui.button(label="Armadura", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def armadura(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaForjaMaterial(self.dueno_id, self.guild_id, "armadura", ficha)
        await interaction.response.edit_message(content="Elige el material a usar:", view=vista)

    @discord.ui.button(label="Cancelar", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaForja(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(content=None, embed=embed_forja(ficha, self.guild_id), view=vista)


class VistaForja(VistaBase):
    def __init__(self, dueno_id, guild_id):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="Empezar a forjar", emoji="🔥", style=discord.ButtonStyle.success)
    async def empezar(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        if ficha["forja_en_progreso"]:
            await interaction.response.send_message("Ya tienes una forja en curso.", ephemeral=True)
            return
        if not ficha["materiales"]:
            await interaction.response.send_message("No tienes materiales para forjar nada.", ephemeral=True)
            return
        vista = VistaForjaTipo(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(content="¿Qué quieres forjar?", embed=None, view=vista)

    @discord.ui.button(label="Recoger", emoji="📦", style=discord.ButtonStyle.primary)
    async def recoger(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        fp = ficha["forja_en_progreso"]
        if not fp:
            await interaction.response.send_message("No tienes ninguna forja en curso.", ephemeral=True)
            return
        if time.time() < fp["termina"]:
            await interaction.response.send_message("Todavía no está lista.", ephemeral=True)
            return
        if fp["exito"]:
            await interaction.response.send_modal(ModalNombreForja(self.dueno_id, self.guild_id))
        else:
            ficha["forja_en_progreso"] = None
            guardar_ficha(self.dueno_id, ficha)
            vista = VistaForja(self.dueno_id, self.guild_id)
            await interaction.response.edit_message(
                content="💥 La forja falló. Los materiales se perdieron, pero puedes intentarlo de nuevo.",
                embed=embed_forja(ficha, self.guild_id), view=vista,
            )

    @discord.ui.button(label="Volver a la ciudad", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaCiudad(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_ciudad(ficha, self.guild_id), view=vista)


# ---------------- Tienda ----------------
def embed_tienda(ficha, guild_id):
    embed = discord.Embed(title="🛒 Tienda de Lubelius", color=0xC9A227)
    embed.add_field(name="Tu dinero", value=moneda(guild_id, ficha["dinero"]), inline=False)

    if ficha["materiales"]:
        top = sorted(ficha["materiales"].items(), key=lambda kv: -PRECIOS_MATERIALES.get(kv[0], 20))[:5]
        texto_mat = "\n".join(f"• {n} x{c} ({PRECIOS_MATERIALES.get(n, 20):,} c/u)" for n, c in top)
        if len(ficha["materiales"]) > 5:
            texto_mat += f"\n… y {len(ficha['materiales']) - 5} más"
    else:
        texto_mat = "No tienes materiales."
    embed.add_field(name="📦 Tus materiales", value=texto_mat[:1024], inline=False)

    conteo_obj = {}
    for o in ficha["objetos"]:
        if o not in (OBJETO_HUEVO_HEROE, OBJETO_SEMILLA_DEMONIO):
            conteo_obj[o] = conteo_obj.get(o, 0) + 1
    if conteo_obj:
        texto_obj = "\n".join(f"• {n} x{c}" for n, c in list(conteo_obj.items())[:5])
    else:
        texto_obj = "No tienes objetos vendibles."
    embed.add_field(name="⚔️ Tus objetos", value=texto_obj[:1024], inline=False)

    embed.set_footer(text="Vende con los botones de abajo o compra una poción en el menú.")
    return embed


class SelectComprarPocion(discord.ui.Select):
    def __init__(self):
        opciones = []
        for tipo in TIPOS_POCION:
            for nivel in (25, 50):
                opciones.append(discord.SelectOption(
                    label=nombre_pocion(tipo, nivel), value=clave_pocion(tipo, nivel),
                    emoji=EMOJI_TIPO_POCION[tipo],
                    description=f"{PRECIOS_POCION[nivel]:,} monedas",
                ))
        super().__init__(placeholder="Comprar una poción...", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        ficha = obtener_ficha(self.view.dueno_id, crear=True)
        clave = self.values[0]
        tipo, nivel_str = clave.rsplit("_", 1)
        nivel = int(nivel_str)
        precio = PRECIOS_POCION[nivel]
        if ficha["dinero"] < precio:
            await interaction.response.send_message(
                f"Te faltan monedas. Cuesta {moneda(self.view.guild_id, precio)} y tienes "
                f"{moneda(self.view.guild_id, ficha['dinero'])}.",
                ephemeral=True,
            )
            return
        ficha["dinero"] -= precio
        ficha["pociones"][clave] = ficha["pociones"].get(clave, 0) + 1
        guardar_ficha(self.view.dueno_id, ficha)
        vista = VistaTienda(self.view.dueno_id, self.view.guild_id)
        await interaction.response.edit_message(
            content=f"✅ Compraste 1x {nombre_pocion(tipo, nivel)}.",
            embed=embed_tienda(ficha, self.view.guild_id), view=vista,
        )


class SelectVenderMaterial(discord.ui.Select):
    def __init__(self, ficha, pagina=0):
        items = sorted(ficha["materiales"].items(), key=lambda kv: (-PRECIOS_MATERIALES.get(kv[0], 20), kv[0]))
        items, self.pagina, self.total = pagina_de(items, pagina)
        opciones = [
            discord.SelectOption(
                label=f"{nombre} x{cantidad}"[:100], value=nombre,
                description=f"{PRECIOS_MATERIALES.get(nombre, 20):,} c/u · total "
                            f"{PRECIOS_MATERIALES.get(nombre, 20) * cantidad:,}"[:100],
            )
            for nombre, cantidad in items
        ]
        placeholder = "Vender TODO tu stock de un material" + (f" ({self.pagina + 1}/{self.total})" if self.total > 1 else "")
        super().__init__(placeholder=placeholder, options=opciones)

    async def callback(self, interaction: discord.Interaction):
        ficha = obtener_ficha(self.view.dueno_id, crear=True)
        nombre = self.values[0]
        cantidad = ficha["materiales"].pop(nombre, 0)
        total = cantidad * PRECIOS_MATERIALES.get(nombre, 20)
        ficha["dinero"] += total
        guardar_ficha(self.view.dueno_id, ficha)
        vista = VistaTienda(self.view.dueno_id, self.view.guild_id)
        await interaction.response.edit_message(
            content=f"✅ Vendiste {cantidad}x {nombre} por {moneda(self.view.guild_id, total)}.",
            embed=embed_tienda(ficha, self.view.guild_id), view=vista,
        )


class VistaVenderMaterial(VistaBase):
    def __init__(self, dueno_id, guild_id, ficha, pagina=0):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id
        select = SelectVenderMaterial(ficha, pagina)
        self.pagina, self.total = select.pagina, select.total
        self.add_item(select)
        if self.total > 1:
            self.add_item(BotonPagina(-1, self.pagina == 0))
            self.add_item(BotonPagina(+1, self.pagina >= self.total - 1))

    def con_pagina(self, pagina):
        return VistaVenderMaterial(self.dueno_id, self.guild_id, obtener_ficha(self.dueno_id, crear=True), pagina)

    @discord.ui.button(label="Volver", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaTienda(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_tienda(ficha, self.guild_id), view=vista)


class SelectVenderObjeto(discord.ui.Select):
    def __init__(self, ficha):
        conteo = {}
        for o in ficha["objetos"]:
            if o in (OBJETO_HUEVO_HEROE, OBJETO_SEMILLA_DEMONIO):
                continue
            conteo[o] = conteo.get(o, 0) + 1
        opciones = [
            discord.SelectOption(
                label=f"{nombre} x{cantidad}"[:100], value=nombre,
                description=f"{PRECIO_OBJETO_GENERICO:,} c/u · total {PRECIO_OBJETO_GENERICO * cantidad:,}",
            )
            for nombre, cantidad in list(conteo.items())[:25]
        ]
        super().__init__(placeholder="Vender TODAS tus copias de un objeto", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        ficha = obtener_ficha(self.view.dueno_id, crear=True)
        nombre = self.values[0]
        cantidad = ficha["objetos"].count(nombre)
        ficha["objetos"] = [o for o in ficha["objetos"] if o != nombre]
        total = cantidad * PRECIO_OBJETO_GENERICO
        ficha["dinero"] += total
        guardar_ficha(self.view.dueno_id, ficha)
        vista = VistaTienda(self.view.dueno_id, self.view.guild_id)
        await interaction.response.edit_message(
            content=f"✅ Vendiste {cantidad}x {nombre} por {moneda(self.view.guild_id, total)}.",
            embed=embed_tienda(ficha, self.view.guild_id), view=vista,
        )


class VistaVenderObjeto(VistaBase):
    def __init__(self, dueno_id, guild_id, ficha):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id
        self.add_item(SelectVenderObjeto(ficha))

    @discord.ui.button(label="Volver", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaTienda(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_tienda(ficha, self.guild_id), view=vista)


class VistaTienda(VistaBase):
    def __init__(self, dueno_id, guild_id):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id
        self.add_item(SelectComprarPocion())

    @discord.ui.button(label="Vender material", emoji="📦", style=discord.ButtonStyle.success)
    async def vender_material(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        if not ficha["materiales"]:
            await interaction.response.send_message("No tienes materiales para vender.", ephemeral=True)
            return
        vista = VistaVenderMaterial(self.dueno_id, self.guild_id, ficha)
        await interaction.response.edit_message(embed=embed_tienda(ficha, self.guild_id), view=vista)

    @discord.ui.button(label="Vender objeto", emoji="⚔️", style=discord.ButtonStyle.success)
    async def vender_objeto(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vendibles = [o for o in ficha["objetos"] if o not in (OBJETO_HUEVO_HEROE, OBJETO_SEMILLA_DEMONIO)]
        if not vendibles:
            await interaction.response.send_message("No tienes objetos vendibles.", ephemeral=True)
            return
        vista = VistaVenderObjeto(self.dueno_id, self.guild_id, ficha)
        await interaction.response.edit_message(embed=embed_tienda(ficha, self.guild_id), view=vista)

    @discord.ui.button(label="Volver a la ciudad", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaCiudad(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_ciudad(ficha, self.guild_id), view=vista)


# ---------------- Gremio ----------------
def embed_gremio(dueno_id, ficha, guild_id):
    g = gremio_estado(ficha)
    rango_jugador = rango_por_ep(ficha["ep"])
    embed = discord.Embed(
        title="🏹 Gremio de Aventureros",
        description="Tablón de misiones de Lubelius. Se renuevan cada día a medianoche (UTC).",
        color=0xC9A227,
    )
    embed.add_field(name="Tu rango", value=rango_jugador, inline=True)
    embed.add_field(name="Tu EP", value=f'{ficha["ep"]:,}', inline=True)

    misiones = MISIONES_GREMIO[rango_jugador]
    if rango_jugador in g["completadas_hoy"]:
        estado = "✅ Ya completaste tu misión de hoy en este rango. Vuelve mañana."
    elif g["en_progreso"]:
        # se busca en el rango con el que se tomó (el jugador pudo subir de rango mientras tanto)
        en_curso = g["en_progreso"]
        m = next((x for x in MISIONES_GREMIO.get(en_curso["rango"], []) if x["id"] == en_curso["id"]), None)
        titulo = m["titulo"] if m else "Misión"
        estado = f'🕓 En curso: **{titulo}** [{en_curso["rango"]}]. Un admin la cerrará con /admin_mision_completar.'
    else:
        dinero_r, exp_r = RECOMPENSAS_RANGO[rango_jugador]
        texto = "\n".join(f'• **{m["titulo"]}** — {m["descripcion"]}' for m in misiones)
        texto += f"\n\nRecompensa: {moneda(guild_id, dinero_r)} y {exp_r:,} EXP."
        estado = texto
    embed.add_field(name=f"Misiones de rango {rango_jugador}", value=estado[:1024], inline=False)
    embed.set_footer(text="Solo puedes tomar misiones de tu rango exacto, y una por rango al día.")
    return embed


class SelectTomarMision(discord.ui.Select):
    def __init__(self, rango_jugador):
        opciones = [
            discord.SelectOption(label=m["titulo"][:100], value=m["id"], description=m["descripcion"][:100])
            for m in MISIONES_GREMIO[rango_jugador]
        ]
        super().__init__(placeholder="Elige una misión para tomar", options=opciones)

    async def callback(self, interaction: discord.Interaction):
        ficha = obtener_ficha(self.view.dueno_id, crear=True)
        g = gremio_estado(ficha)
        rango_jugador = rango_por_ep(ficha["ep"])
        if rango_jugador in g["completadas_hoy"] or g["en_progreso"]:
            guardar_ficha(self.view.dueno_id, ficha)
            await interaction.response.send_message("Esa misión ya no está disponible para ti.", ephemeral=True)
            return
        mision = next(m for m in MISIONES_GREMIO[rango_jugador] if m["id"] == self.values[0])
        g["en_progreso"] = {"rango": rango_jugador, "id": mision["id"]}
        guardar_ficha(self.view.dueno_id, ficha)
        vista = VistaGremio(self.view.dueno_id, self.view.guild_id)
        await interaction.response.edit_message(
            content=f'✅ Tomaste **{mision["titulo"]}**. Cuando la termines en el rol, '
                    "un admin la cerrará con /admin_mision_completar.",
            embed=vista.crear_embed(), view=vista,
        )


class VistaGremio(VistaBase):
    def __init__(self, dueno_id, guild_id):
        super().__init__(dueno_id, timeout=300)
        self.guild_id = guild_id
        ficha = obtener_ficha(dueno_id, crear=True)
        g = gremio_estado(ficha)
        guardar_ficha(dueno_id, ficha)
        rango_jugador = rango_por_ep(ficha["ep"])
        if not g["en_progreso"] and rango_jugador not in g["completadas_hoy"]:
            self.add_item(SelectTomarMision(rango_jugador))

    def crear_embed(self):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        return embed_gremio(self.dueno_id, ficha, self.guild_id)

    @discord.ui.button(label="Volver a la ciudad", emoji="⬅️", style=discord.ButtonStyle.secondary)
    async def volver(self, interaction: discord.Interaction, button: discord.ui.Button):
        ficha = obtener_ficha(self.dueno_id, crear=True)
        vista = VistaCiudad(self.dueno_id, self.guild_id)
        await interaction.response.edit_message(embed=embed_ciudad(ficha, self.guild_id), view=vista)

@bot.tree.command(name="ciudad", description="Visita Lubelius: tienda, gremio, casino, posada y forja")
@app_commands.guild_only()
async def ciudad(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    if not ficha["raza_id"]:
        await interaction.response.send_message("Primero elige tu raza con /raza.", ephemeral=True)
        return
    vista = VistaCiudad(interaction.user.id, interaction.guild_id)
    await interaction.response.send_message(embed=embed_ciudad(ficha, interaction.guild_id), view=vista)


def _texto_item_equipable(item, rareza_bonus):
    emoji = EMOJI_RAREZA_FORJA[item["rareza"]]
    bonus = rareza_bonus.get(item["rareza"], 0)
    sufijo = f" (+{bonus}%)" if item["tipo"] == "arma" else f" (+{bonus} resistencia)"
    return f'{emoji} {item["nombre"]} — {NOMBRE_RAREZA_FORJA[item["rareza"]]}{sufijo}'


@bot.tree.command(name="equipar", description="Equipa un arma o armadura que hayas forjado o recibido")
@app_commands.describe(nombre="El arma o armadura a equipar (busca por nombre)")
@app_commands.guild_only()
async def equipar(interaction: discord.Interaction, nombre: str):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    # el autocompletado manda el id de la pieza; si escribieron el nombre a mano, se busca por nombre
    item_id = nombre if nombre in ficha["forjados"] else next(
        (iid for iid, it in ficha["forjados"].items() if it["nombre"].lower() == nombre.lower()), None
    )
    if item_id is None:
        await interaction.response.send_message("No tienes ningún objeto con ese nombre.", ephemeral=True)
        return
    item = ficha["forjados"][item_id]
    ficha["equipado"][item["tipo"]] = item_id
    guardar_ficha(interaction.user.id, ficha)
    rareza_bonus = BONUS_ARMA if item["tipo"] == "arma" else BONUS_ARMADURA
    await interaction.response.send_message(f"✅ Equipaste: {_texto_item_equipable(item, rareza_bonus)}")


@equipar.autocomplete("nombre")
async def equipar_autocomplete(interaction: discord.Interaction, current: str):
    ficha = obtener_ficha(interaction.user.id, crear=True)
    current = current.lower()
    equipados = set(ficha["equipado"].values())
    return [
        app_commands.Choice(
            name=f'{EMOJI_RAREZA_FORJA[it["rareza"]]} {it["nombre"]} ({it["tipo"]}){" ✅" if iid in equipados else ""}'[:100],
            value=iid,
        )
        for iid, it in ficha["forjados"].items() if current in it["nombre"].lower()
    ][:25]


@bot.tree.command(name="desequipar", description="Te quitas el arma o la armadura equipada")
@app_commands.describe(tipo="Qué quieres quitarte")
@app_commands.choices(tipo=[
    app_commands.Choice(name="Arma", value="arma"),
    app_commands.Choice(name="Armadura", value="armadura"),
])
@app_commands.guild_only()
async def desequipar(interaction: discord.Interaction, tipo: app_commands.Choice[str]):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    ficha = obtener_ficha(interaction.user.id, crear=True)
    ficha["equipado"][tipo.value] = None
    guardar_ficha(interaction.user.id, ficha)
    await interaction.response.send_message(f"✅ Te quitaste tu {tipo.name.lower()}.")

