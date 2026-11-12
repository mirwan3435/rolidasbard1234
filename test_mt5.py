import MetaTrader5 as mt5

if not mt5.initialize():
    print("GAGAL konek:", mt5.last_error())
    quit()

info = mt5.terminal_info()
acc = mt5.account_info()
print("Terminal :", info.name, "| connected:", info.connected)
print("Server   :", acc.server)
print("Akun demo:", acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO)

for s in ["XAUUSD", "EURUSD", "USDJPY"]:
    mt5.symbol_select(s, True)
    tick = mt5.symbol_info_tick(s)
    sym = mt5.symbol_info(s)
    if tick is None or sym is None:
        print(s, "-> data kosong, cek nama simbol")
        continue
    print(s, "| bid", tick.bid, "| ask", tick.ask, "| spread(points)", sym.spread)

mt5.shutdown()
