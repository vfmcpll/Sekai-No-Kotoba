import os
import time
import discord
from discord import app_commands

from nucleo import *


TRADES_ARCHIVO = os.path.join(DATA_DIR, "trades.json")
TRADE_EXPIRA_SEGUNDOS = 15 * 60   # un trueque sin terminar se cancela solo a los 15 minutos

_TRADES = registrar_almacen(AlmacenJSON(TRADES_ARCHIVO, lambda: {"activos": {}, "trades": {}}))


def cargar_trades():
    datos = _TRADES.cargar()
    datos.setdefault("activos", {})
    datos.setdefault("trades", {})
    return datos


def guardar_trades(datos):
    _TRADES.datos = datos
    _TRADES.marcar()


def _clave_activo(guild_id, uid):
    return f"{guild_id}:{uid}"


def trade_de(guild_id, uid):
    """Devuelve (trade, datos_completos) del trueque activo de ese usuario en ese servidor, o (None, datos).
    Si el trueque ya venció, se cierra solo."""
    datos = cargar_trades()
    clave = _clave_activo(guild_id, uid)
    tid = datos["activos"].get(clave)
    if tid is None:
        return None, datos
    trade = datos["trades"].get(tid)
    if trade is None:   # quedó una referencia huérfana
        datos["activos"].pop(clave, None)
        guardar_trades(datos)
        return None, datos
    if time.time() - trade.get("creado", time.time()) > TRADE_EXPIRA_SEGUNDOS:
        _cerrar_trade(datos, trade)
        guardar_trades(datos)
        return None, datos
    return trade, datos


def _cerrar_trade(datos, trade):
    datos["trades"].pop(trade["id"], None)
    datos["activos"].pop(_clave_activo(trade["guild_id"], trade["a"]), None)
    datos["activos"].pop(_clave_activo(trade["guild_id"], trade["b"]), None)


def _quitar_item(ficha, tipo, nombre, cantidad):
    """Intenta quitar 'cantidad' de un material, objeto, arma o armadura.
    Devuelve (True, rareza) si pudo (rareza solo aplica a arma/armadura), o (False, None)."""
    if tipo == "material":
        if ficha["materiales"].get(nombre, 0) < cantidad:
            return False, None
        ficha["materiales"][nombre] -= cantidad
        if ficha["materiales"][nombre] <= 0:
            del ficha["materiales"][nombre]
        return True, None
    if tipo in ("arma", "armadura"):
        item_id = next(
            (iid for iid, it in ficha["forjados"].items() if it["nombre"] == nombre and it["tipo"] == tipo), None
        )
        if item_id is None:
            return False, None
        item = ficha["forjados"].pop(item_id)
        for slot, equipado_id in list(ficha["equipado"].items()):
            if equipado_id == item_id:
                ficha["equipado"][slot] = None
        return True, item["rareza"]
    if ficha["objetos"].count(nombre) < cantidad:
        return False, None
    for _ in range(cantidad):
        ficha["objetos"].remove(nombre)
    return True, None


def _dar_item(ficha, tipo, nombre, cantidad, rareza=None):
    if tipo == "material":
        ficha["materiales"][nombre] = ficha["materiales"].get(nombre, 0) + cantidad
    elif tipo in ("arma", "armadura"):
        item_id = nuevo_id_objeto()
        ficha["forjados"][item_id] = {"nombre": nombre, "tipo": tipo, "rareza": rareza or "comun"}
    else:
        ficha["objetos"].extend([nombre] * cantidad)


def _inventario_de(uid):
    ficha = obtener_ficha(uid, crear=True)
    nombres = set(ficha["materiales"].keys())
    nombres.update(ficha["objetos"])
    nombres.update(it["nombre"] for it in ficha["forjados"].values())
    return sorted(nombres)


def _disponible_de(uid, nombre):
    ficha = obtener_ficha(uid, crear=True)
    if nombre in ficha["materiales"]:
        return ficha["materiales"][nombre]
    if any(it["nombre"] == nombre for it in ficha["forjados"].values()):
        return 1
    return ficha["objetos"].count(nombre)


def _tipo_de(uid, nombre):
    ficha = obtener_ficha(uid, crear=True)
    if nombre in ficha["materiales"]:
        return "material"
    for it in ficha["forjados"].values():
        if it["nombre"] == nombre:
            return it["tipo"]
    return "objeto"


def _texto_oferta(oferta):
    if not oferta:
        return "Nada todavía"
    return "\n".join(f"• {it['cantidad']}x {it['nombre']}" for it in oferta)


def embed_trade(trade, nombre_a, nombre_b):
    a, b = str(trade["a"]), str(trade["b"])
    check_a = "✅" if trade["confirmado"][a] else "⏳"
    check_b = "✅" if trade["confirmado"][b] else "⏳"
    embed = discord.Embed(title="🔁 Trueque", color=0x2ECC71 if all(trade["confirmado"].values()) else 0xC9A227)
    embed.add_field(name=f"{check_a} {nombre_a} ofrece", value=_texto_oferta(trade["ofertas"][a]), inline=True)
    embed.add_field(name=f"{check_b} {nombre_b} ofrece", value=_texto_oferta(trade["ofertas"][b]), inline=True)
    if trade["estado"] == "pendiente":
        embed.set_footer(text=f"Esperando a que {nombre_b} use /trade aceptar")
    else:
        embed.set_footer(text="Usa /trade agregar, /trade quitar y /trade confirmar. Cualquier cambio quita las confirmaciones.")
    return embed


def _nombre_usuario(trade, uid):
    """Nombre guardado al abrir el trueque (en un titulo de embed las menciones no se ven)."""
    return trade.get("nombres", {}).get(str(uid), "Jugador")


async def _responder_trade(interaction, trade, texto=None):
    embed = embed_trade(trade, _nombre_usuario(trade, trade["a"]), _nombre_usuario(trade, trade["b"]))
    await interaction.response.send_message(content=texto, embed=embed)


trade_group = app_commands.Group(
    name="trade", description="Intercambia materiales y objetos con otro jugador", guild_only=True
)


@trade_group.command(name="abrir", description="Abre una propuesta de trueque con otro jugador")
@app_commands.describe(usuario="Con quién quieres intercambiar")
async def trade_abrir(interaction: discord.Interaction, usuario: discord.Member):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    if usuario.bot or usuario.id == interaction.user.id:
        await interaction.response.send_message("Elige a otro jugador para intercambiar.", ephemeral=True)
        return
    propio, datos = trade_de(interaction.guild_id, interaction.user.id)
    if propio is not None:
        await interaction.response.send_message(
            "Ya tienes un trueque activo. Usa /trade cancelar primero.", ephemeral=True
        )
        return
    ajeno, datos = trade_de(interaction.guild_id, usuario.id)
    if ajeno is not None:
        await interaction.response.send_message(f"{usuario.display_name} ya tiene un trueque activo.", ephemeral=True)
        return

    tid = str(int(time.time() * 1000))
    trade = {
        "id": tid, "guild_id": interaction.guild_id,
        "a": interaction.user.id, "b": usuario.id,
        "nombres": {str(interaction.user.id): interaction.user.display_name, str(usuario.id): usuario.display_name},
        "creado": time.time(),
        "estado": "pendiente",
        "ofertas": {str(interaction.user.id): [], str(usuario.id): []},
        "confirmado": {str(interaction.user.id): False, str(usuario.id): False},
    }
    datos["trades"][tid] = trade
    datos["activos"][_clave_activo(interaction.guild_id, interaction.user.id)] = tid
    datos["activos"][_clave_activo(interaction.guild_id, usuario.id)] = tid
    guardar_trades(datos)

    await _responder_trade(
        interaction, trade, f"{usuario.mention}, te proponen un trueque. Usa **/trade aceptar** para abrirlo."
    )


@trade_group.command(name="aceptar", description="Acepta la propuesta de trueque que te hicieron")
async def trade_aceptar(interaction: discord.Interaction):
    if not puede_jugar(interaction):
        await interaction.response.send_message(MENSAJE_SIN_PERMISO_JUGAR, ephemeral=True)
        return
    trade, datos = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None or trade["estado"] != "pendiente" or trade["b"] != interaction.user.id:
        await interaction.response.send_message(
            "No tienes ninguna propuesta de trueque esperando tu aceptación.", ephemeral=True
        )
        return
    trade["estado"] = "abierto"
    guardar_trades(datos)
    await _responder_trade(interaction, trade, "✅ Trueque abierto. Ambos pueden usar /trade agregar y /trade quitar.")


@trade_group.command(name="agregar", description="Añade algo de lo tuyo a tu oferta del trueque activo")
@app_commands.describe(nombre="Material u objeto a añadir", cantidad="Cuántos")
async def trade_agregar(interaction: discord.Interaction, nombre: str, cantidad: app_commands.Range[int, 1, 1_000_000]):
    trade, datos = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None or trade["estado"] != "abierto":
        await interaction.response.send_message("No tienes un trueque abierto ahora mismo.", ephemeral=True)
        return
    uid = str(interaction.user.id)
    ya_ofrecido = sum(it["cantidad"] for it in trade["ofertas"][uid] if it["nombre"] == nombre)
    disponible = _disponible_de(interaction.user.id, nombre)
    if ya_ofrecido + cantidad > disponible:
        await interaction.response.send_message(
            f"No tienes suficiente: tienes {disponible}x {nombre} y ya ofreciste {ya_ofrecido}.", ephemeral=True
        )
        return
    entrada = next((it for it in trade["ofertas"][uid] if it["nombre"] == nombre), None)
    if entrada:
        entrada["cantidad"] += cantidad
    else:
        trade["ofertas"][uid].append(
            {"tipo": _tipo_de(interaction.user.id, nombre), "nombre": nombre, "cantidad": cantidad}
        )
    trade["confirmado"] = {k: False for k in trade["confirmado"]}
    guardar_trades(datos)
    await _responder_trade(interaction, trade)


@trade_agregar.autocomplete("nombre")
async def trade_agregar_autocomplete(interaction: discord.Interaction, current: str):
    current = current.lower()
    return [
        app_commands.Choice(name=n, value=n) for n in _inventario_de(interaction.user.id) if current in n.lower()
    ][:25]


@trade_group.command(name="quitar", description="Quita algo de tu propia oferta del trueque activo")
@app_commands.describe(nombre="Qué quitar de tu oferta", cantidad="Cuántos")
async def trade_quitar(interaction: discord.Interaction, nombre: str, cantidad: app_commands.Range[int, 1, 1_000_000]):
    trade, datos = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None or trade["estado"] != "abierto":
        await interaction.response.send_message("No tienes un trueque abierto ahora mismo.", ephemeral=True)
        return
    uid = str(interaction.user.id)
    entrada = next((it for it in trade["ofertas"][uid] if it["nombre"] == nombre), None)
    if entrada is None or entrada["cantidad"] < cantidad:
        await interaction.response.send_message(f"No tienes {nombre} en tu oferta (o no tantos).", ephemeral=True)
        return
    entrada["cantidad"] -= cantidad
    if entrada["cantidad"] <= 0:
        trade["ofertas"][uid].remove(entrada)
    trade["confirmado"] = {k: False for k in trade["confirmado"]}
    guardar_trades(datos)
    await _responder_trade(interaction, trade)


@trade_quitar.autocomplete("nombre")
async def trade_quitar_autocomplete(interaction: discord.Interaction, current: str):
    trade, _ = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None:
        return []
    current = current.lower()
    nombres = [it["nombre"] for it in trade["ofertas"].get(str(interaction.user.id), [])]
    return [app_commands.Choice(name=n, value=n) for n in nombres if current in n.lower()][:25]


@trade_group.command(name="confirmar", description="Confirma tu parte del trueque activo")
async def trade_confirmar(interaction: discord.Interaction):
    trade, datos = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None or trade["estado"] != "abierto":
        await interaction.response.send_message("No tienes un trueque abierto ahora mismo.", ephemeral=True)
        return
    uid = str(interaction.user.id)
    trade["confirmado"][uid] = True
    guardar_trades(datos)

    if not all(trade["confirmado"].values()):
        await _responder_trade(interaction, trade, "Confirmado de tu parte. Falta la otra persona.")
        return

    a, b = trade["a"], trade["b"]
    oferta_a, oferta_b = trade["ofertas"][str(a)], trade["ofertas"][str(b)]
    valido = (
        all(_disponible_de(a, it["nombre"]) >= it["cantidad"] for it in oferta_a)
        and all(_disponible_de(b, it["nombre"]) >= it["cantidad"] for it in oferta_b)
    )
    if not valido:
        _cerrar_trade(datos, trade)
        guardar_trades(datos)
        await interaction.response.send_message(
            "❌ Uno de los dos ya no tiene lo que había puesto en la mesa. El trueque se canceló."
        )
        return

    ficha_a, ficha_b = obtener_ficha(a, crear=True), obtener_ficha(b, crear=True)
    for it in oferta_a:
        ok, rareza = _quitar_item(ficha_a, it["tipo"], it["nombre"], it["cantidad"])
        if ok:
            _dar_item(ficha_b, it["tipo"], it["nombre"], it["cantidad"], rareza)
    for it in oferta_b:
        ok, rareza = _quitar_item(ficha_b, it["tipo"], it["nombre"], it["cantidad"])
        if ok:
            _dar_item(ficha_a, it["tipo"], it["nombre"], it["cantidad"], rareza)
    guardar_ficha(a, ficha_a)
    guardar_ficha(b, ficha_b)

    _cerrar_trade(datos, trade)
    guardar_trades(datos)
    await _responder_trade(interaction, trade, "✅ ¡Trueque completado!")


@trade_group.command(name="cancelar", description="Cancela tu trueque activo")
async def trade_cancelar(interaction: discord.Interaction):
    trade, datos = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None:
        await interaction.response.send_message("No tienes un trueque activo.", ephemeral=True)
        return
    _cerrar_trade(datos, trade)
    guardar_trades(datos)
    await interaction.response.send_message("❌ Trueque cancelado.")


@trade_group.command(name="ver", description="Muestra el estado de tu trueque activo")
async def trade_ver(interaction: discord.Interaction):
    trade, _ = trade_de(interaction.guild_id, interaction.user.id)
    if trade is None:
        await interaction.response.send_message("No tienes un trueque activo.", ephemeral=True)
        return
    await _responder_trade(interaction, trade)

bot.tree.add_command(trade_group)

