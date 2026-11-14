// POSMGR. Tangan per tick. Default TIDAK berdagang.
// Sambungkan nanti. Dashboard tidak menyalakan EnableTrading.
#property strict
input bool EnableTrading = false;
input int PairPoints = 5;

struct Pair {
   double sl;
   double stopOrder;
};

double PairStop(double sl, int direction) {
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if (direction > 0) return sl + PairPoints * point;
   return sl - PairPoints * point;
}

void OnTick() {
   if (!EnableTrading) return;
   // Tempat perintah dari data/posmgr/commands.json.
   // Saat EnableTrading true, SL dan stop order harus berpasangan.
   // Tidak boleh ada stop order terisi tanpa SL.
}
