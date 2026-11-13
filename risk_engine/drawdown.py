class DrawdownMonitor:
    """Pantau kerugian sesi dan drawdown dari puncak equity (equity virtual)."""

    def __init__(self, start_equity):
        self.equity = start_equity
        self.peak = start_equity
        self.session_start = start_equity

    def start_session(self, equity):
        self.session_start = equity

    def update(self, equity):
        self.equity = equity
        self.peak = max(self.peak, equity)

    def status(self, cfg):
        daily = max(0.0, (self.session_start - self.equity) / self.session_start * 100)
        dd = max(0.0, (self.peak - self.equity) / self.peak * 100)
        return {
            "daily_loss_pct": daily,
            "drawdown_pct": dd,
            "daily_breach": daily >= cfg["daily_loss_limit_pct"],
            "total_breach": dd >= cfg["max_drawdown_pct"],
        }
