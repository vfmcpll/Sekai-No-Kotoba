# ============================================================
#  RAZAS DE TENSURA
#  Aqui se editan las razas, sus beneficios y sus evoluciones.
#  - "dano": porcentaje extra de dano de ese tipo
#  - "res":  porcentaje de resistencia (reduce el dano recibido de ese tipo)
#  - En cada evolucion los numeros son el TOTAL de esa etapa (no se suman).
#  - "dificultad" (1 a 5): a mayor dificultad, mas experiencia cuesta cada
#    evolucion, pero mas EP inicial y mas EP gana al evolucionar.
#  - La experiencia se gana matando monstruos (se hace mas adelante).
# ============================================================

# Dificultad: numero -> (nombre, multiplicador de experiencia)
DIFICULTADES = {
    1: ("Fácil", 1.0),
    2: ("Normal", 1.5),
    3: ("Difícil", 2.5),
    4: ("Muy difícil", 4.0),
    5: ("Legendaria", 7.0),
}

# EP (Puntos de Existencia) con los que empieza cada raza segun su dificultad
EP_INICIAL = {1: 100, 2: 200, 3: 400, 4: 800, 5: 1500}

# Experiencia base para evolucionar (se multiplica por etapa^2 y por la dificultad)
EXP_BASE = 500

# Tipos (para escribir mas corto)
F, M = "Físico", "Mágico"
FUE, HIE, RAY = "Fuego", "Hielo", "Rayo"
VIE, TIE, AGU = "Viento", "Tierra", "Agua"
SAG, OSC = "Sagrado", "Oscuro"
VEN, PAR, MEN = "Veneno", "Parálisis", "Mental"

CATEGORIAS = {
    "humanos": {
        "nombre": "Humanos y Semihumanos", "emoji": "🧑",
        "descripcion": "Humanos, elfos, enanos, ogros, sirenas y homúnculos",
    },
    "bestias": {
        "nombre": "Hombres bestia", "emoji": "🐺",
        "descripcion": "Licántropos, felinos, zorros y harpías",
    },
    "monstruos": {
        "nombre": "Monstruos", "emoji": "👹",
        "descripcion": "Goblins, orcos, lobos, lagartos y bestias mágicas",
    },
    "espiritus": {
        "nombre": "Espíritus y Slimes", "emoji": "🟦",
        "descripcion": "Slimes, espíritus elementales, hadas y dríades",
    },
    "superiores": {
        "nombre": "Seres Superiores", "emoji": "✨",
        "descripcion": "Ángeles, demonios, vampiros, dragones y no-muertos",
    },
}

RAZAS = {}


def _r(rid, nombre, cat, emoji, dificultad, desc, dano, res, evo):
    """
    Cada elemento de 'evo' es normalmente una tupla (nombre, dano, res): la
    exp y el EP de esa etapa se calculan solos.
    Para una etapa especial (que necesite mucha mas exp/EP, como las que
    superan 1,000,000 de EP) se puede usar un diccionario en su lugar:
      {"nombre": ..., "dano": {...}, "res": {...},
       "exp": 300000, "ep": 700000, "ep_min": 1_000_000}
    "ep_min" es un requisito EXTRA de EP acumulado para poder evolucionar
    a esa etapa (ademas de la experiencia). Se deja en None si no aplica.
    """
    ep_ini = EP_INICIAL[dificultad]
    mult = DIFICULTADES[dificultad][1]
    etapas = []
    for i, datos in enumerate(evo, start=1):
        if isinstance(datos, dict):
            etapas.append({
                "nombre": datos["nombre"],
                "dano": datos.get("dano", {}),
                "res": datos.get("res", {}),
                "exp": datos.get("exp", int(EXP_BASE * i * i * mult)),
                "ep": datos.get("ep", ep_ini * 4 * i),
                "ep_min": datos.get("ep_min"),
            })
        else:
            n, d, r = datos
            etapas.append({
                "nombre": n, "dano": d, "res": r,
                "exp": int(EXP_BASE * i * i * mult),   # experiencia necesaria para llegar aqui
                "ep": ep_ini * 4 * i,                  # EP que gana al evolucionar a esta etapa
                "ep_min": None,
            })
    RAZAS[rid] = {
        "nombre": nombre, "cat": cat, "emoji": emoji, "dificultad": dificultad,
        "desc": desc, "dano": dano, "res": res,
        "ep_inicial": ep_ini, "evo": etapas,
    }


# ---------------- HUMANOS Y SEMIHUMANOS ----------------
_r("humano", "Humano", "humanos", "🧑", 1,
   "Débiles al nacer, pero versátiles. Dominan el aura y las artes marciales.",
   {F: 5, SAG: 5}, {MEN: 5},
   [("Santo", {F: 15, SAG: 15}, {OSC: 10, MEN: 10}),
    ("Santo Completo", {F: 30, SAG: 30, M: 10}, {OSC: 25, MEN: 20, F: 10})])

_r("elfo", "Elfo", "humanos", "🧝", 2,
   "Longevos y con gran afinidad mágica.",
   {M: 10, VIE: 5}, {M: 10},
   [("Alto Elfo", {M: 20, VIE: 10}, {M: 20, MEN: 10}),
    ("Elfo Ancestral", {M: 35, VIE: 15, SAG: 10}, {M: 30, MEN: 20})])

_r("enano", "Enano", "humanos", "⛏️", 2,
   "Artesanos resistentes, expertos en la forja.",
   {F: 10, FUE: 5}, {FUE: 10, F: 5},
   [("Enano Superior", {F: 20, FUE: 10}, {FUE: 20, F: 10, TIE: 10}),
    ("Rey Enano", {F: 30, FUE: 20}, {FUE: 30, F: 20, TIE: 20})])

_r("ogro", "Ogro", "humanos", "🗡️", 2,
   "Guerreros de fuerza bruta. Con un nombre pueden evolucionar a Kijin.",
   {F: 15}, {F: 10},
   [("Kijin", {F: 25, FUE: 10}, {F: 15, M: 10, FUE: 10}),
    ("Oni", {F: 40, FUE: 20}, {F: 25, M: 20, FUE: 20, PAR: 10})])

_r("sirena", "Sirena / Tritón", "humanos", "🧜", 2,
   "Seres marinos con gran afinidad al agua.",
   {AGU: 10}, {AGU: 20},
   [("Ser Marino Superior", {AGU: 20, M: 10}, {AGU: 40, HIE: 10}),
    ("Señor del Mar", {AGU: 35, M: 20}, {AGU: 60, HIE: 20, RAY: 10})])

_r("homunculo", "Homúnculo", "humanos", "🧪", 2,
   "Cuerpos artificiales creados con magia y alquimia.",
   {M: 10}, {VEN: 15, MEN: 10},
   [("Homúnculo Superior", {M: 20}, {VEN: 30, MEN: 20}),
    ("Homúnculo Perfecto", {M: 35}, {VEN: 50, MEN: 30, M: 15})])

# ---------------- HOMBRES BESTIA ----------------
_r("hombre_lobo", "Hombre Lobo", "bestias", "🐺", 2,
   "Licántropos veloces y feroces.",
   {F: 12}, {F: 5},
   [("Licántropo Alfa", {F: 22, VIE: 5}, {F: 10, VEN: 10}),
    ("Rey Lobo", {F: 35, VIE: 10}, {F: 20, VEN: 20, MEN: 10})])

_r("hombre_gato", "Hombre Gato", "bestias", "🐱", 1,
   "Ágiles y sigilosos.",
   {F: 8, VIE: 7}, {VIE: 10},
   [("Gato Cazador", {F: 16, VIE: 12}, {VIE: 20, F: 5}),
    ("Rey Felino", {F: 28, VIE: 20}, {VIE: 30, F: 10, OSC: 10})])

_r("hombre_leon", "Hombre León", "bestias", "🦁", 3,
   "Guerreros orgullosos de enorme fuerza.",
   {F: 15, FUE: 5}, {F: 10},
   [("León Guerrero", {F: 25, FUE: 10}, {F: 20, FUE: 10}),
    ("Rey León", {F: 40, FUE: 20}, {F: 30, FUE: 20, MEN: 15})])

_r("hombre_zorro", "Hombre Zorro", "bestias", "🦊", 2,
   "Astutos y con afinidad a la magia.",
   {M: 10, FUE: 5}, {MEN: 10},
   [("Zorro Místico", {M: 20, FUE: 12}, {MEN: 20, M: 10}),
    ("Zorro Espiritual", {M: 35, FUE: 20}, {MEN: 35, M: 20})])

_r("harpia", "Harpía", "bestias", "🦅", 2,
   "Seres alados que dominan los cielos y el viento.",
   {VIE: 12}, {VIE: 15, RAY: 5},
   [("Harpía Superior", {VIE: 22, F: 8}, {VIE: 30, RAY: 10}),
    ("Reina Harpía", {VIE: 38, F: 15}, {VIE: 45, RAY: 20, MEN: 10})])

# ---------------- MONSTRUOS ----------------
_r("goblin", "Goblin", "monstruos", "👺", 1,
   "Débiles al inicio, pero evolucionan con un nombre.",
   {F: 5}, {VEN: 5},
   [("Hobgoblin", {F: 15}, {F: 10, VEN: 10}),
    ("Señor Goblin", {F: 28, M: 5}, {F: 15, VEN: 15, M: 5})])

_r("orco", "Orco", "monstruos", "🐗", 2,
   "Robustos y voraces.",
   {F: 12}, {F: 12, VEN: 5},
   [("Alto Orco", {F: 22}, {F: 20, VEN: 10}),
    ("Señor Orco", {F: 35, OSC: 5}, {F: 30, VEN: 20, OSC: 10}),
    ("Desastre Orco", {F: 50, OSC: 15}, {F: 45, VEN: 30, OSC: 20, MEN: 15})])

_r("lobo_colmillos", "Lobo de Colmillos", "monstruos", "🐕", 2,
   "Cazadores de manada, rápidos y letales.",
   {F: 12, VIE: 3}, {VIE: 5},
   [("Lobo Tempestad", {F: 22, VIE: 12, RAY: 8}, {VIE: 15, RAY: 10, F: 10}),
    ("Lobo Estelar Tempestad", {F: 38, VIE: 20, RAY: 20}, {VIE: 30, RAY: 25, F: 20, OSC: 10})])

_r("lagarto", "Hombre Lagarto", "monstruos", "🦎", 2,
   "Guerreros de los pantanos con escamas duras.",
   {F: 10}, {F: 10, AGU: 10},
   [("Dragonewt", {F: 22, FUE: 8}, {F: 20, AGU: 10, FUE: 10}),
    ("Semidragón", {F: 35, FUE: 15}, {F: 30, FUE: 20, AGU: 15, M: 10})])

_r("serpiente", "Serpiente Negra", "monstruos", "🐍", 2,
   "Serpientes de veneno letal.",
   {VEN: 15}, {VEN: 25},
   [("Serpiente Tempestad", {VEN: 28, F: 10, RAY: 5}, {VEN: 45, F: 10}),
    ("Serpiente Ancestral", {VEN: 42, F: 20, RAY: 12}, {VEN: 65, F: 20, PAR: 15})])

_r("arana", "Araña Gigante", "monstruos", "🕷️", 2,
   "Tejedoras de hilos resistentes y venenosos.",
   {VEN: 12, F: 5}, {VEN: 20},
   [("Arácnido (Aracne)", {VEN: 22, F: 12}, {VEN: 35, F: 10}),
    ("Reina Aracne", {VEN: 35, F: 20, M: 10}, {VEN: 50, F: 20, M: 10})])

_r("insectoide", "Insectoide", "monstruos", "🐜", 2,
   "Enjambres de exoesqueleto duro.",
   {F: 12}, {F: 15, VEN: 10},
   [("Insecto Gigante", {F: 24}, {F: 28, VEN: 20}),
    ("Rey Insecto", {F: 40, VEN: 10}, {F: 45, VEN: 35, PAR: 15})])

_r("tigre_cuchilla", "Tigre Cuchilla", "monstruos", "🐅", 2,
   "Depredadores veloces de garras afiladas.",
   {F: 15, VIE: 5}, {F: 5},
   [("Tigre Cuchilla Alfa", {F: 26, VIE: 10}, {F: 12, VIE: 8}),
    ("Tigre Cuchilla Real", {F: 40, VIE: 18}, {F: 22, VIE: 15, MEN: 10})])

_r("armorsaurio", "Armorsaurio", "monstruos", "🦖", 3,
   "Bestias blindadas de resistencia enorme.",
   {F: 10}, {F: 25, FUE: 10},
   [("Armorsaurio Acorazado", {F: 20}, {F: 40, FUE: 20}),
    ("Armorsaurio Ancestral", {F: 32, TIE: 10}, {F: 55, FUE: 30, TIE: 20})])

# ---------------- ESPIRITUS Y SLIMES ----------------
_r("slime", "Slime", "espiritus", "🟦", 2,
   "Cuerpo flexible que absorbe y se adapta. Gran resistencia física.",
   {M: 8}, {F: 20, PAR: 10},
   [("Slime Demoníaco", {M: 22, OSC: 10}, {F: 35, PAR: 20, VEN: 15}),
    ("Ultimate Slime", {M: 40, OSC: 20, SAG: 10}, {F: 50, M: 20, PAR: 30, VEN: 30, MEN: 15})])

_r("espiritu_fuego", "Espíritu de Fuego", "espiritus", "🔥", 3,
   "Encarnación del fuego, como Ifrit.",
   {FUE: 20}, {FUE: 40},
   [("Espíritu Mayor de Fuego", {FUE: 35, M: 10}, {FUE: 60, MEN: 10}),
    ("Señor del Fuego", {FUE: 55, M: 20}, {FUE: 80, MEN: 20})])

_r("espiritu_agua", "Espíritu de Agua", "espiritus", "💧", 3,
   "Encarnación del agua y el hielo.",
   {AGU: 20}, {AGU: 40},
   [("Espíritu Mayor de Agua", {AGU: 35, HIE: 10}, {AGU: 60, HIE: 15}),
    ("Señor del Agua", {AGU: 55, HIE: 20}, {AGU: 80, HIE: 30})])

_r("espiritu_viento", "Espíritu de Viento", "espiritus", "🌪️", 3,
   "Encarnación del viento y las tormentas.",
   {VIE: 20}, {VIE: 40},
   [("Espíritu Mayor de Viento", {VIE: 35, RAY: 10}, {VIE: 60, RAY: 15}),
    ("Señor del Viento", {VIE: 55, RAY: 20}, {VIE: 80, RAY: 30})])

_r("espiritu_tierra", "Espíritu de Tierra", "espiritus", "⛰️", 3,
   "Encarnación de la tierra y la roca.",
   {TIE: 20}, {TIE: 40, F: 10},
   [("Espíritu Mayor de Tierra", {TIE: 35}, {TIE: 60, F: 20}),
    ("Señor de la Tierra", {TIE: 55, F: 10}, {TIE: 80, F: 35})])

_r("hada", "Hada", "espiritus", "🧚", 2,
   "Diminutas y muy mágicas.",
   {M: 12}, {M: 15, MEN: 5},
   [("Hada Superior", {M: 25}, {M: 30, MEN: 15}),
    ("Reina Hada", {M: 40, SAG: 10}, {M: 45, MEN: 25})])

_r("driade", "Dríade", "espiritus", "🌳", 3,
   "Espíritus del bosque con poder sobre la naturaleza.",
   {M: 10, TIE: 8}, {VEN: 15, TIE: 10},
   [("Gran Dríade", {M: 22, TIE: 15}, {VEN: 30, TIE: 20, MEN: 10}),
    ("Espíritu del Bosque", {M: 38, TIE: 25}, {VEN: 45, TIE: 35, MEN: 20})])

_r("ent", "Ent (Treant)", "espiritus", "🌲", 2,
   "Árboles vivientes de gran fuerza y resistencia.",
   {F: 12, TIE: 8}, {F: 20, VEN: 10},
   [("Ent Ancestral", {F: 24, TIE: 15}, {F: 35, VEN: 20, TIE: 10}),
    ("Guardián del Bosque", {F: 38, TIE: 25}, {F: 50, VEN: 30, TIE: 20})])

# ---------------- SERES SUPERIORES ----------------
_r("angel", "Ángel", "superiores", "👼", 4,
   "Seres espirituales de luz y orden.",
   {SAG: 20, M: 10}, {SAG: 30, OSC: 15},
   [("Arcángel", {SAG: 35, M: 20}, {SAG: 50, OSC: 30, MEN: 15}),
    ("Serafín", {SAG: 55, M: 35}, {SAG: 70, OSC: 45, MEN: 30}),
    {"nombre": "Serafín Supremo", "dano": {SAG: 90, M: 55}, "res": {SAG: 100, OSC: 65, MEN: 45},
     "exp": 340_000, "ep": 1_600_000, "ep_min": 1_000_000}])

_r("demonio", "Demonio Menor", "superiores", "😈", 4,
   "Seres espirituales de oscuridad y magia. Crecen en poder con el tiempo.",
   {OSC: 20, M: 10}, {OSC: 30, FUE: 10},
   [("Demonio Mayor", {OSC: 30, M: 18}, {OSC: 45, FUE: 15, MEN: 10}),
    ("Archidemonio", {OSC: 45, M: 30}, {OSC: 60, FUE: 25, MEN: 20}),
    ("Demon Peer", {OSC: 60, M: 45}, {OSC: 75, FUE: 35, MEN: 30})])

_r("vampiro", "Vampiro", "superiores", "🧛", 3,
   "Nobles de la noche con gran poder oscuro.",
   {OSC: 15, F: 8}, {OSC: 20, VEN: 10},
   [("Vampiro Verdadero", {OSC: 28, F: 15}, {OSC: 35, VEN: 20, HIE: 10}),
    ("Ancestro Vampiro", {OSC: 45, F: 25}, {OSC: 55, VEN: 35, HIE: 20, MEN: 15})])

_r("dragon", "Cría de Dragón", "superiores", "🐲", 5,
   "Jóvenes dragones con un potencial inmenso.",
   {F: 20, FUE: 10}, {F: 20, FUE: 20},
   [("Dragón Joven", {F: 35, M: 20, FUE: 20}, {F: 35, M: 20, FUE: 30}),
    ("Dragón Ancestral", {F: 55, M: 45, FUE: 30}, {F: 55, M: 45, FUE: 40, MEN: 40}),
    {"nombre": "Dragón Verdadero", "dano": {F: 90, M: 70, FUE: 50}, "res": {F: 85, M: 70, FUE: 60, MEN: 55},
     "exp": 360_000, "ep": 1_800_000, "ep_min": 1_000_000}])

_r("no_muerto", "No-muerto", "superiores", "💀", 2,
   "Cuerpos sin vida animados por magia oscura.",
   {OSC: 12, VEN: 5}, {VEN: 50, OSC: 20, MEN: 20},
   [("No-muerto Superior", {OSC: 24, F: 10}, {VEN: 70, OSC: 30, MEN: 30}),
    ("Señor No-muerto", {OSC: 40, F: 20}, {VEN: 90, OSC: 45, MEN: 45})])


# ---------------- Formas finales: Héroe Verdadero y Rey Demonio Verdadero ----------------
# No son razas elegibles con /raza (su "cat" no aparece en CATEGORIAS, asi que
# nunca salen en el buscador normal). Solo se llega a ellas con el comando
# /evolucion_definitiva, que exige estar en la evolucion maxima de la raza
# actual, 500,000 EP, 500,000 EXP y un Huevo de Héroe o una Semilla de Rey Demonio.
_r("heroe_verdadero", "Héroe Verdadero", "especial", "🌟", 5,
   "Un Héroe Verdadero, bendecido por un Huevo de Héroe.",
   {F: 70, SAG: 70, M: 35}, {OSC: 55, MEN: 45, F: 30}, [])

_r("rey_demonio_verdadero", "Rey Demonio Verdadero", "especial", "👑", 5,
   "Un Rey Demonio Verdadero, nacido de una Semilla de Rey Demonio.",
   {OSC: 100, M: 75, F: 25}, {OSC: 90, FUE: 55, MEN: 50}, [])


# ---------------- Utilidades ----------------
def texto_beneficios(dano, res):
    lineas = []
    if dano:
        lineas.append("⚔️ **Daño:** " + ", ".join(f"{t} +{v}%" for t, v in dano.items()))
    if res:
        lineas.append("🛡️ **Resistencias:** " + ", ".join(f"{t} {v}%" for t, v in res.items()))
    return "\n".join(lineas) or "Sin beneficios"


def nombre_etapa(raza_id, etapa):
    raza = RAZAS[raza_id]
    if etapa <= 0 or etapa > len(raza["evo"]):
        return raza["nombre"]
    return raza["evo"][etapa - 1]["nombre"]


def beneficios_etapa(raza_id, etapa):
    """Devuelve (dano, res) de la etapa indicada (0 = raza base)."""
    raza = RAZAS[raza_id]
    if etapa <= 0 or etapa > len(raza["evo"]):
        return raza["dano"], raza["res"]
    evo = raza["evo"][etapa - 1]
    return evo["dano"], evo["res"]


def texto_dificultad(dificultad):
    nombre = DIFICULTADES[dificultad][0]
    return f"{'🔥' * dificultad} {nombre}"


def exp_necesaria(raza_id, etapa):
    """Experiencia para pasar de la etapa actual a la siguiente (None si ya es la ultima)."""
    evo = RAZAS[raza_id]["evo"]
    if etapa >= len(evo):
        return None
    return evo[etapa]["exp"]


def ep_al_evolucionar(raza_id, etapa):
    """EP que se ganan al pasar de la etapa actual a la siguiente (None si ya es la ultima)."""
    evo = RAZAS[raza_id]["evo"]
    if etapa >= len(evo):
        return None
    return evo[etapa]["ep"]


def ep_min_necesario(raza_id, etapa):
    """EP minimo (ademas de la experiencia) para evolucionar a la siguiente etapa, o None si no aplica."""
    evo = RAZAS[raza_id]["evo"]
    if etapa >= len(evo):
        return None
    return evo[etapa].get("ep_min")
