import os
import json
import copy
import random
import time
import datetime
import asyncio
import atexit
import signal
import threading
import traceback
import discord
from discord import app_commands

from razas import (
    RAZAS, CATEGORIAS,
    texto_beneficios, texto_dificultad,
    nombre_etapa, beneficios_etapa, exp_necesaria,
    ep_al_evolucionar, ep_min_necesario,
)
from combate import (
    ZONAS, ZONAS_ORDENADAS, MONSTRUOS,
    vida_maxima, energia_maxima, ataque_base_jugador,
    multiplicador_dano, reduccion_dano,
    zonas_disponibles, elegir_monstruo, tirar_materiales,
    calcular_golpe,
    ATAQUES_NORMALES, ATAQUES_ESPECIALES, MENSAJES_FALLO, MENSAJES_CRITICO,
    COOLDOWN_ESPECIAL_TURNOS, PROB_ESPECIAL_MONSTRUO,
    TODOS_LOS_MATERIALES, PRECIOS_MATERIALES, RAREZA_MATERIALES, ORDEN_RAREZA_FORJA,
)
from habilidades import (
    HABILIDADES, RAREZA_NOMBRE, RAREZA_EMOJI, RAREZA_COLOR,
    resistencia_total, habilidades_activas,
    COSTO_ROLL, COSTO_RULETA, PESOS_ROLL, PESOS_RULETA, tirar_habilidad,
)

# En Railway: Variables -> DISCORD_TOKEN. (TOKEN y token.txt siguen funcionando por compatibilidad.)
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
if not TOKEN and os.path.exists("token.txt"):
    TOKEN = open("token.txt").read().strip()
if not TOKEN:
    raise SystemExit("❌ Falta el token: define la variable DISCORD_TOKEN en Railway (Variables).")

# En Railway el disco se borra en cada deploy: monta un Volume y pon DATA_DIR=/data
# (o la ruta donde lo montes) para que fichas/config/trueques sobrevivan.
DATA_DIR = os.getenv("DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
ARCHIVO = os.path.join(DATA_DIR, "fichas.json")
CONFIG_ARCHIVO = os.path.join(DATA_DIR, "config.json")
INTERVALO_GUARDADO = 5   # segundos entre guardados a disco (solo si hubo cambios)

FICHA_BASE = {
    "raza": "Sin definir",
    "raza_id": None,
    "etapa": 0,
    "ep": 0,
    "exp": 0,
    "habilidades": [],
    "objetos": [],
    "materiales": {},
    "cooldowns": {},   # {zona_id: momento (segundos desde epoch) en que vuelve a estar libre}
    "mejoras": {"dano": 0, "dano_especial": 0, "vida": 0, "energia": 0, "resistencias": {}},
    "dinero": 0,
    "pociones": {},   # {"vida_25": 2, "energia_50": 1, ...}
    "gremio": {"fecha": "", "completadas_hoy": [], "en_progreso": None},
    "descansado": False,
    "descanso_fecha": "",
    "forjados": {},    # {id: {"nombre":str, "tipo":"arma"|"armadura", "rareza":str}}
    "equipado": {"arma": None, "armadura": None},
    "forja_en_progreso": None,  # {"tipo","rareza","termina","exito","material","cantidad"}
}

def fecha_hoy():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def gremio_estado(ficha):
    """Devuelve ficha['gremio'], reiniciando 'completadas_hoy' y 'en_progreso' si ya es otro dia."""
    hoy = fecha_hoy()
    g = ficha["gremio"]
    if g["fecha"] != hoy:
        g["fecha"] = hoy
        g["completadas_hoy"] = []
        g["en_progreso"] = None
    return g

RAREZA_FORJA = ["comun", "extra", "unica", "definitiva", "genesis"]
NOMBRE_RAREZA_FORJA = {"comun": "Común", "extra": "Extra", "unica": "Única", "definitiva": "Definitiva", "genesis": "Génesis"}
EMOJI_RAREZA_FORJA = {"comun": "⚪", "extra": "🔵", "unica": "🟣", "definitiva": "🟡", "genesis": "🌈"}

# % extra de daño que da un arma equipada de cada rareza (Genesis solo se otorga, no se forja)
BONUS_ARMA = {"comun": 5, "extra": 12, "unica": 25, "definitiva": 45, "genesis": 80}
# puntos de resistencia que da una armadura equipada (sin categoria Genesis)
BONUS_ARMADURA = {"comun": 5, "extra": 12, "unica": 25, "definitiva": 45}

CANTIDAD_IDEAL_FORJA = {"comun": 10, "extra": 20, "unica": 35, "definitiva": 60}
TIEMPO_FORJA_MINUTOS = {"comun": 10, "extra": 30, "unica": 90, "definitiva": 240}

# Las unicas armas Genesis son las originales de la novela; solo el dueño del servidor las da.
ARMAS_GENESIS = {
    "elpis": {"nombre": "Elpis", "descripcion": "La espada dragónica de Rimuru Tempest, creada con un núcleo de Dragón Ancestral."},
    "world": {"nombre": "World", "descripcion": "Espada creada por Veldanava; el arma predilecta de Guy Crimson."},
    "asura": {"nombre": "Asura", "descripcion": "El arma que Guy Crimson entregó a Milim Nava."},
}


def probabilidad_exito_forja(cantidad, ideal):
    """Muy pocos materiales o demasiados bajan la probabilidad; el punto ideal da el mejor exito."""
    ratio = cantidad / ideal
    if ratio <= 1:
        return 0.25 + 0.65 * ratio
    exceso = ratio - 1
    return max(0.35, 0.90 - 0.30 * exceso)


def es_dueno_servidor(interaction: discord.Interaction) -> bool:
    return bool(interaction.guild) and interaction.guild.owner_id == interaction.user.id


def nuevo_id_objeto():
    return f"{int(time.time() * 1000)}_{random.randint(100, 999)}"

PUNTOS_POR_EP = 10
MEJORA_POR_PUNTO = 0.001
ELEMENTOS_RESISTENCIA = [
    "Físico", "Mágico", "Fuego", "Hielo", "Rayo", "Viento", "Tierra",
    "Agua", "Sagrado", "Oscuro", "Veneno", "Parálisis", "Mental",
]

def puntos_gastados_total(ficha):
    m = ficha["mejoras"]
    return m["dano"] + m["dano_especial"] + m["vida"] + m["energia"] + sum(m["resistencias"].values())


def puntos_disponibles(ficha):
    return ficha["ep"] // PUNTOS_POR_EP - puntos_gastados_total(ficha)

# ---------------- Almacenamiento: en memoria + guardado atomico ----------------
class AlmacenJSON:
    """Mantiene un JSON en memoria y lo escribe a disco solo cuando cambia.
    La escritura es atomica (archivo temporal + os.replace): si el bot se cae a mitad
    de guardar, el archivo anterior queda intacto en vez de quedar a medias."""

    def __init__(self, ruta, defecto):
        self.ruta = ruta
        self._defecto = defecto
        self.datos = None
        self.sucio = False
        self._candado = threading.Lock()

    def cargar(self):
        if self.datos is None:
            self.datos = self._leer()
        return self.datos

    def _leer(self):
        if os.path.exists(self.ruta):
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                copia = f"{self.ruta}.corrupto-{int(time.time())}"
                try:
                    os.replace(self.ruta, copia)
                except OSError:
                    pass
                print(f"⚠️ {self.ruta} estaba dañado; guardé una copia en {copia} y empiezo de cero.")
        return self._defecto()

    def marcar(self):
        self.sucio = True

    def serializar(self):
        """Devuelve el texto a escribir, o None si no hay cambios. Va en el hilo principal."""
        if not self.sucio or self.datos is None:
            return None
        self.sucio = False
        return json.dumps(self.datos, ensure_ascii=False, separators=(",", ":"))

    def escribir(self, texto):
        with self._candado:
            tmp = self.ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(texto)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.ruta)

    def volcar(self):
        texto = self.serializar()
        if texto is None:
            return
        try:
            self.escribir(texto)
        except OSError:
            self.sucio = True
            raise


ALMACENES = []


def registrar_almacen(almacen):
    ALMACENES.append(almacen)
    return almacen


_FICHAS = registrar_almacen(AlmacenJSON(ARCHIVO, dict))
_CONFIGS = registrar_almacen(AlmacenJSON(CONFIG_ARCHIVO, dict))


def guardar_todo_sync():
    for almacen in ALMACENES:
        try:
            almacen.volcar()
        except OSError as e:
            print(f"⚠️ No pude guardar {almacen.ruta}: {e}")


atexit.register(guardar_todo_sync)


async def bucle_guardado():
    """Cada pocos segundos escribe a disco lo que haya cambiado (sin bloquear el bot)."""
    while True:
        await asyncio.sleep(INTERVALO_GUARDADO)
        for almacen in ALMACENES:
            texto = almacen.serializar()
            if texto is None:
                continue
            try:
                await asyncio.to_thread(almacen.escribir, texto)
            except OSError as e:
                almacen.sucio = True
                print(f"⚠️ No pude guardar {almacen.ruta}: {e}")


CONFIG_BASE = {"admin_roles": [], "jugador_roles": [], "moneda_emoji": "🪙", "misiones": []}


def cargar_config():
    return _CONFIGS.cargar()


def guardar_config(datos):
    _CONFIGS.datos = datos
    _CONFIGS.marcar()


def config_guild(guild_id):
    """Devuelve (y crea si hace falta) la configuracion de un servidor."""
    datos = _CONFIGS.cargar()
    gid = str(guild_id)
    conf = datos.get(gid)
    if conf is None:
        conf = copy.deepcopy(CONFIG_BASE)
        datos[gid] = conf
        _CONFIGS.marcar()
    else:
        for clave, valor in CONFIG_BASE.items():
            if clave not in conf:
                conf[clave] = copy.deepcopy(valor)
    return conf


def guardar_config_guild(guild_id, conf):
    _CONFIGS.cargar()[str(guild_id)] = conf
    _CONFIGS.marcar()


def moneda(guild_id, cantidad):
    emoji = config_guild(guild_id)["moneda_emoji"]
    return f"{cantidad:,} {emoji}"

def es_admin(interaction: discord.Interaction) -> bool:
    """Administrador de Discord SIEMPRE cuenta, ademas de cualquier rol configurado como admin del bot."""
    if interaction.user.guild_permissions.administrator:
        return True
    conf = config_guild(interaction.guild_id)
    ids_admin = set(conf["admin_roles"])
    return any(r.id in ids_admin for r in interaction.user.roles)


def puede_jugar(interaction: discord.Interaction) -> bool:
    """Si no hay roles de jugador configurados, cualquiera puede usar el bot."""
    if es_admin(interaction):
        return True
    conf = config_guild(interaction.guild_id)
    ids_jugador = conf["jugador_roles"]
    if not ids_jugador:
        return True
    ids_jugador = set(ids_jugador)
    return any(r.id in ids_jugador for r in interaction.user.roles)

MENSAJE_SIN_PERMISO_JUGAR = "No tienes un rol habilitado para usar este bot en este servidor."
MENSAJE_SIN_PERMISO_ADMIN = "No tienes permiso para usar este comando (hace falta un rol de administrador del bot)."

# Usuarios con un combate en curso ahora mismo (se pierde si el bot se reinicia)
BATALLAS_ACTIVAS = set()

# Objetos especiales: caen con poca probabilidad al ganar CUALQUIER combate
OBJETO_HUEVO_HEROE = "Huevo de Héroe"
OBJETO_SEMILLA_DEMONIO = "Semilla de Rey Demonio"
# Objetos con nombre fijo que /admin_objeto sugiere solo; se puede seguir escribiendo cualquier otro nombre libre
OBJETOS_CONOCIDOS = [OBJETO_HUEVO_HEROE, OBJETO_SEMILLA_DEMONIO]
PROB_HUEVO_HEROE = 0.002       # 0.2% por victoria
PROB_SEMILLA_DEMONIO = 0.002   # 0.2% por victoria

# Requisitos para /evolucion_definitiva
EP_MINIMO_TRASCENDER = 500_000   # se exige, pero NO se gasta
EXP_COSTO_TRASCENDER = 500_000   # se exige Y se gasta

RANGOS_MISION = [
    ("F", 0),
    ("E", 300),
    ("D", 1_000),
    ("C", 5_000),
    ("B", 25_000),
    ("A", 100_000),
    ("Special A", 300_000),
]

# 3 misiones fijas por rango. Se reinician cada dia; solo se puede completar 1 por rango al dia,
# y solo se puede tomar la del rango que tengas EXACTAMENTE (segun tu EP).
RECOMPENSAS_RANGO = {
    "F": (50, 20), "E": (150, 80), "D": (400, 250), "C": (1_200, 900),
    "B": (4_000, 3_500), "A": (15_000, 15_000), "Special A": (60_000, 60_000),
}

MISIONES_GREMIO = {
    "F": [
        {"id": "f1", "titulo": "Limpieza de la plaza", "descripcion": "Ayuda a retirar escombros de la plaza de Lubelius tras la feria."},
        {"id": "f2", "titulo": "Mensajero novato", "descripcion": "Lleva un mensaje sellado entre dos comerciantes de la ciudad."},
        {"id": "f3", "titulo": "Ratas en las alcantarillas", "descripcion": "Elimina un nido de ratas gigantes bajo el barrio bajo."},
    ],
    "E": [
        {"id": "e1", "titulo": "Escolta de mercader", "descripcion": "Acompaña a un mercader hasta la aldea vecina y protégelo del camino."},
        {"id": "e2", "titulo": "Plaga de slimes", "descripcion": "Controla una plaga de slimes salvajes cerca de las murallas."},
        {"id": "e3", "titulo": "Hierbas medicinales", "descripcion": "Recolecta hierbas raras en el borde del Bosque de Jura."},
    ],
    "D": [
        {"id": "d1", "titulo": "Bandidos en el camino", "descripcion": "Un grupo de bandidos ataca caravanas en el camino real."},
        {"id": "d2", "titulo": "Goblins merodeadores", "descripcion": "Aleja a una partida de goblins que se acerca demasiado a la ciudad."},
        {"id": "d3", "titulo": "Bestia herida", "descripcion": "Una bestia herida y asustada aterroriza a los granjeros locales."},
    ],
    "C": [
        {"id": "c1", "titulo": "Orcos en la frontera", "descripcion": "Se reportan orcos organizándose cerca de la frontera del reino."},
        {"id": "c2", "titulo": "Artefacto perdido", "descripcion": "Recupera un artefacto sellado en unas ruinas cercanas."},
        {"id": "c3", "titulo": "Escolta diplomática menor", "descripcion": "Protege a un noble en un trayecto largo y peligroso."},
    ],
    "B": [
        {"id": "b1", "titulo": "Guarida de bandoleros", "descripcion": "Un líder bandolero poderoso comanda una guarida fortificada."},
        {"id": "b2", "titulo": "Lobo de colmillos alfa", "descripcion": "Una manada de Lobos de Colmillos con un alfa muy agresivo acecha la zona."},
        {"id": "b3", "titulo": "Desapariciones nocturnas", "descripcion": "Investiga extrañas desapariciones que podrían ser obra de un no-muerto."},
    ],
    "A": [
        {"id": "a1", "titulo": "Amenaza de nivel Disaster", "descripcion": "Un monstruo cercano al umbral catastrófico fue avistado en la región."},
        {"id": "a2", "titulo": "Escolta a otro reino", "descripcion": "Escolta a una comitiva diplomática hasta un reino lejano."},
        {"id": "a3", "titulo": "Mazmorra ancestral", "descripcion": "Explora las ruinas de una mazmorra que nadie ha completado."},
    ],
    "Special A": [
        {"id": "sa1", "titulo": "Amenaza Catastrophe", "descripcion": "Un monstruo de rango Catastrophe pone en peligro a toda la región."},
        {"id": "sa2", "titulo": "Negociación con demonios", "descripcion": "Una facción de demonios exige negociar directamente con un Special A."},
        {"id": "sa3", "titulo": "Sello debilitado", "descripcion": "Un antiguo sello se está debilitando y algo enorme quiere salir."},
    ],
}


def rango_por_ep(ep):
    actual = RANGOS_MISION[0][0]
    for nombre, minimo in RANGOS_MISION:
        if ep >= minimo:
            actual = nombre
    return actual


def rango_index(nombre_rango):
    for i, (nombre, _) in enumerate(RANGOS_MISION):
        if nombre == nombre_rango:
            return i
    return 0


PRECIO_OBJETO_GENERICO = 500   # objetos sin precio propio (armas/objetos de rol) se venden por este fijo
PRECIOS_POCION = {25: 200, 50: 500}
COOLDOWN_POCION_RONDAS = 3
TIPOS_POCION = ["vida", "energia", "dano"]
NOMBRES_TIPO_POCION = {"vida": "Vida", "energia": "Energía", "dano": "Daño"}
EMOJI_TIPO_POCION = {"vida": "❤️", "energia": "⚡", "dano": "⚔️"}


def clave_pocion(tipo, nivel):
    return f"{tipo}_{nivel}"


def nombre_pocion(tipo, nivel):
    return f"Poción de {NOMBRES_TIPO_POCION[tipo]} ({nivel}%)"

_VERIFICADAS = set()   # fichas ya revisadas en esta ejecucion (campos nuevos rellenados)


def cargar():
    return _FICHAS.cargar()


def guardar(datos):
    _FICHAS.datos = datos
    _FICHAS.marcar()


def _completar(ficha):
    """Rellena los campos que falten (fichas viejas) sin tocar los que ya existen."""
    for clave, valor in FICHA_BASE.items():
        if clave not in ficha:
            ficha[clave] = copy.deepcopy(valor)
        elif isinstance(valor, dict) and isinstance(ficha[clave], dict):
            for k, v in valor.items():
                if k not in ficha[clave]:
                    ficha[clave][k] = copy.deepcopy(v)


def obtener_ficha(uid, crear=False):
    """Devuelve la ficha (el objeto real en memoria). Si no existe y crear=True, la crea.
    Ojo: lo que se cambie en la ficha queda en memoria; llama guardar_ficha para que se escriba a disco."""
    datos = _FICHAS.cargar()
    clave = str(uid)
    ficha = datos.get(clave)
    if ficha is None:
        if not crear:
            return None
        ficha = {}
        datos[clave] = ficha
        _FICHAS.marcar()
    if clave not in _VERIFICADAS:
        _completar(ficha)
        _VERIFICADAS.add(clave)
        _FICHAS.marcar()
    return ficha


def guardar_ficha(uid, ficha):
    _FICHAS.cargar()[str(uid)] = ficha
    _FICHAS.marcar()

RAZAS_TRASCENDENTES = {"heroe_verdadero", "rey_demonio_verdadero"}


def ya_evoluciono(ficha):
    """Si ya avanzo con su raza, no puede cambiarla. Trascender es siempre definitivo."""
    if ficha["raza_id"] in RAZAS_TRASCENDENTES:
        return True
    return bool(ficha["raza_id"]) and (ficha["etapa"] > 0 or ficha["exp"] > 0)


# ---------------- Tiempo / enfriamientos de zonas ----------------
def zona_lista(ficha, zid):
    """True si la zona esta desbloqueada por EP y no esta en enfriamiento."""
    z = ZONAS[zid]
    if ficha["ep"] < z["ep_min"]:
        return False
    disponible_en = ficha.get("cooldowns", {}).get(zid, 0)
    return time.time() >= disponible_en


def segundos_restantes(ficha, zid):
    disponible_en = ficha.get("cooldowns", {}).get(zid, 0)
    return max(0, int(disponible_en - time.time()))


def texto_tiempo(segundos):
    minutos, seg = divmod(segundos, 60)
    if minutos > 0:
        return f"{minutos} min" + (f" {seg}s" if minutos < 3 else "")
    return f"{seg}s"


def texto_zonas(ficha):
    ep = ficha["ep"]
    lineas = []
    for zid in ZONAS_ORDENADAS:
        z = ZONAS[zid]
        if ep < z["ep_min"]:
            lineas.append(f'🔒 {z["nombre"]} — necesitas {z["ep_min"]:,} EP (tienes {ep:,})')
        elif not zona_lista(ficha, zid):
            lineas.append(f'⏳ {z["emoji"]} {z["nombre"]} — disponible en {texto_tiempo(segundos_restantes(ficha, zid))}')
        else:
            lineas.append(f'{z["emoji"]} **{z["nombre"]}** — desbloqueada')
    return "\n".join(lineas)


# ---------------- Textos y embeds ----------------
def _recortar_lineas(lineas, limite):
    extra = len(lineas) - limite
    if extra > 0:
        lineas = lineas[:limite] + [f"…y {extra} más"]
    return "\n".join(lineas)[:1024]


def como_lista(items, limite=10):
    if not items:
        return "Ninguna"
    conteo = {}
    for i in items:
        conteo[i] = conteo.get(i, 0) + 1
    lineas = [f"• {n}" + (f" ×{c}" if c > 1 else "") for n, c in conteo.items()]
    return _recortar_lineas(lineas, limite)


ORDEN_RAREZA = {r: i for i, r in enumerate(RAREZA_NOMBRE)}  # comun=0, extra=1, unica=2, definitiva=3


def habilidades_como_texto(habilidades_ids, limite=14):
    if not habilidades_ids:
        return "Ninguna"
    conteo = {}
    for hid in habilidades_ids:
        conteo[hid] = conteo.get(hid, 0) + 1
    conocidas = [(HABILIDADES[hid], c) for hid, c in conteo.items() if hid in HABILIDADES]
    desconocidas = [(hid, c) for hid, c in conteo.items() if hid not in HABILIDADES]
    # las mas raras primero
    conocidas.sort(key=lambda hc: (-ORDEN_RAREZA[hc[0]["rareza"]], hc[0]["nombre"]))

    lineas = [
        f'{RAREZA_EMOJI[h["rareza"]]} {h["nombre"]}' + (f" ×{c}" if c > 1 else "")
        for h, c in conocidas
    ]
    lineas += [f"• {hid}" + (f" ×{c}" if c > 1 else "") for hid, c in desconocidas]  # texto libre de antes del catalogo
    return _recortar_lineas(lineas, limite)


def materiales_como_texto(materiales, limite=12):
    if not materiales:
        return "Ninguno"
    items = sorted(materiales.items(), key=lambda kv: (-kv[1], kv[0]))
    return _recortar_lineas([f"• {nombre} ×{cant:,}" for nombre, cant in items], limite)


def barra_exp(actual, maximo, ancho=10):
    """Barra de progreso fina para la experiencia (distinta a la de vida/energia)."""
    maximo = max(1, maximo)
    llenos = max(0, min(ancho, int(ancho * actual / maximo)))
    return "▰" * llenos + "▱" * (ancho - llenos)


def crear_embed_perfil(usuario, ficha):
    raza_id = ficha["raza_id"]
    rango = rango_por_ep(ficha["ep"])
    if raza_id in RAZAS:
        emoji = RAZAS[raza_id]["emoji"]
        raza_txt = nombre_etapa(raza_id, ficha["etapa"])
        siguiente = exp_necesaria(raza_id, ficha["etapa"])
        if siguiente is None:
            exp_txt = f'{ficha["exp"]:,}\n✨ Etapa máxima'
        else:
            exp_txt = f'{barra_exp(ficha["exp"], siguiente)}\n{ficha["exp"]:,} / {siguiente:,}'
            ep_req = ep_min_necesario(raza_id, ficha["etapa"])
            if ep_req:
                exp_txt += f'\n🔒 Pide también {ep_req:,} EP'
    else:
        emoji = "👤"
        raza_txt = "Sin definir"
        exp_txt = f'{ficha["exp"]:,}'

    embed = discord.Embed(
        title=f"{emoji} {usuario.display_name}",
        description=f"**{raza_txt}** · 🎖️ Rango **{rango}**",
        color=0x3BA9F5,
    )
    embed.set_thumbnail(url=usuario.display_avatar.url)
    embed.add_field(name="⚡ EP", value=f'{ficha["ep"]:,}', inline=True)
    embed.add_field(name="💰 Dinero", value=moneda(usuario.guild.id, ficha["dinero"]), inline=True)
    embed.add_field(name="📈 Experiencia", value=exp_txt, inline=True)

    if raza_id in RAZAS:
        dano, res = beneficios_etapa(raza_id, ficha["etapa"])
        vm = vida_maxima(raza_id, ficha["etapa"])
        em = energia_maxima(raza_id, ficha["etapa"])
        embed.add_field(name="Vida / Energía máx.", value=f"❤️ {vm:,}  ⚡ {em:,}", inline=False)
        embed.add_field(name="Beneficios de raza", value=texto_beneficios(dano, res), inline=False)

    embed.add_field(name="✨ Habilidades", value=habilidades_como_texto(ficha["habilidades"]), inline=False)
    embed.add_field(name="🎒 Objetos / Armas", value=como_lista(ficha["objetos"]), inline=True)
    embed.add_field(name="📦 Materiales", value=materiales_como_texto(ficha["materiales"]), inline=True)

    if ficha["forjados"]:
        equipo = ficha["equipado"]
        lineas_forja = []
        for iid, it in ficha["forjados"].items():
            marca = " ✅" if iid in (equipo["arma"], equipo["armadura"]) else ""
            lineas_forja.append(f'{EMOJI_RAREZA_FORJA[it["rareza"]]} {it["nombre"]} — {it["tipo"]}{marca}')
        embed.add_field(name="🔨 Forjados", value=_recortar_lineas(lineas_forja, 8), inline=False)
    embed.add_field(name="📊 Mejoras de estadísticas", value=mejoras_como_texto(ficha), inline=False)
    embed.set_footer(text="✅ = equipado")
    return embed


def pct(puntos):
    """Convierte una cantidad de puntos en el % real que representan (puntos * 0.1%)."""
    valor = puntos * MEJORA_POR_PUNTO * 100
    return int(valor) if valor == int(valor) else round(valor, 2)


def mejoras_como_texto(ficha):
    m = ficha["mejoras"]
    lineas = []
    if m["dano"]:
        lineas.append(f'⚔️ Daño +{pct(m["dano"])}%')
    if m["dano_especial"]:
        lineas.append(f'✨ Daño Especial +{pct(m["dano_especial"])}%')
    if m["vida"]:
        lineas.append(f'❤️ Vida +{pct(m["vida"])}%')
    if m["energia"]:
        lineas.append(f'⚡ Energía +{pct(m["energia"])}%')
    for elemento, pts in m["resistencias"].items():
        lineas.append(f'🛡️ Resistencia a {elemento} +{pct(pts)}%')
    lineas.append(f'🔸 Puntos disponibles: {puntos_disponibles(ficha):,} (1 cada {PUNTOS_POR_EP} EP = +0.1%)')
    return "\n".join(lineas)

def embed_raza(raza_id):
    r = RAZAS[raza_id]
    embed = discord.Embed(title=f'{r["emoji"]} {r["nombre"]}', description=r["desc"], color=0x3BA9F5)
    embed.add_field(name="Dificultad", value=texto_dificultad(r["dificultad"]), inline=True)
    embed.add_field(name="EP inicial", value=f'{r["ep_inicial"]:,}', inline=True)
    embed.add_field(name="Beneficios base", value=texto_beneficios(r["dano"], r["res"]), inline=False)
    for i, e in enumerate(r["evo"], start=1):
        valor = (
            texto_beneficios(e["dano"], e["res"])
            + f'\n📈 Exp necesaria: {e["exp"]:,} · ⚡ +{e["ep"]:,} EP'
        )
        if e.get("ep_min"):
            valor += f'\n🔒 También requiere {e["ep_min"]:,} EP acumulado'
        embed.add_field(name=f'Evolución {i}: {e["nombre"]}', value=valor, inline=False)
    embed.set_footer(text="Los beneficios de cada evolución son los totales de esa etapa (no se suman).")
    return embed


TEXTO_CATEGORIAS = "🌟 **Elige tu raza de Tensura**\nPrimero elige una categoría."
TEXTO_RAZAS = "Elige una raza de esta categoría para ver sus beneficios."

class VistaBase(discord.ui.View):
    def __init__(self, dueno_id, timeout=300):
        super().__init__(timeout=timeout)
        self.dueno_id = dueno_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.dueno_id:
            await interaction.response.send_message("Este menú no es tuyo.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)
        await avisar_error(interaction)

def barra(actual, maximo, ancho=10, tipo="vida"):
    """Barra de vida (verde/amarillo/rojo segun cuanto quede) o de energia (azul)."""
    actual = max(0, actual)
    maximo = max(1, maximo)
    llenos = min(ancho, round(ancho * actual / maximo))
    if actual > 0 and llenos == 0:
        llenos = 1   # si aun queda algo, nunca se ve completamente vacia
    if tipo == "energia":
        relleno = "🟦"
    else:
        fraccion = actual / maximo
        relleno = "🟩" if fraccion > 0.5 else "🟨" if fraccion > 0.25 else "🟥"
    return relleno * llenos + "⬛" * (ancho - llenos)


MENSAJE_ERROR_GENERICO = "⚠️ Algo salió mal. Inténtalo de nuevo en un momento."


async def avisar_error(interaction, mensaje=MENSAJE_ERROR_GENERICO):
    """Responde al usuario sin importar si la interaccion ya fue respondida."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(mensaje, ephemeral=True)
        else:
            await interaction.response.send_message(mensaje, ephemeral=True)
    except discord.HTTPException:
        pass


class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self._tarea_guardado = None

    async def setup_hook(self):
        self._tarea_guardado = asyncio.create_task(bucle_guardado())
        # Railway apaga el contenedor con SIGTERM: cerramos bien para guardar todo antes de salir
        try:
            asyncio.get_running_loop().add_signal_handler(
                signal.SIGTERM, lambda: asyncio.ensure_future(self.close())
            )
        except (NotImplementedError, RuntimeError):
            pass   # Windows
        await self.tree.sync()

    async def close(self):
        if self._tarea_guardado:
            self._tarea_guardado.cancel()
        guardar_todo_sync()
        await super().close()


bot = Bot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    traceback.print_exception(type(error), error, error.__traceback__)
    await avisar_error(interaction)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
