from __future__ import annotations

def manage_live_exits(tracker) -> None:
    """Best-effort manager for live positions: if SL/TP/trailing is hit, submit a market sell via CCXT and persist state.
    This is intentionally simple for safety; it acts only when live mode is enabled and an executor exists.
    """
    try:
        if tracker.auto_trade_mode != 'live' or tracker.live_executor is None:
            return
        # Map symbols to current prices via aggregator results
        enabled_map = {cid: cfg.symbol for cid, cfg in tracker.config.tracked_coins.items() if not cfg.disabled}
        aggregated = tracker.aggregator.aggregate_prices(enabled_map)
        sym_to_price: dict[str, float] = {}
        for cid, pdata in (aggregated or {}).items():
            try:
                price = pdata.get('price') if isinstance(pdata, dict) else None
                sym = (tracker.config.tracked_coins.get(cid).symbol.upper() if cid in tracker.config.tracked_coins else None)
                if price is not None and sym:
                    sym_to_price[sym] = float(price)
            except Exception:
                continue
        # For each open position, check exits (confirm via exchange open orders)
        for sym, pos in list(tracker.portfolio.positions.items()):
            # Backoff handling: skip symbol if in backoff window
            try:
                st = tracker._live_exit_backoff.get(sym)
                if st and time.time() < float(st.get('next_ts', 0.0)):
                    continue
            except Exception:
                pass
            current_price = sym_to_price.get(sym)
            if current_price is None:
                continue
            # Update peak
            pos.update_peak(float(current_price))
            # Live break-even: if unrealized R>=1 and not armed yet, arm a stop at entry
            try:
                if tracker.live_executor is not None and not tracker._live_be_armed.get(sym, False):
                    # Compute RR vs current SL estimate based on ATR params
                    coin_id = None
                    for cid, cfgc in tracker.config.tracked_coins.items():
                        if cfgc.symbol.upper() == sym:
                            coin_id = cid
                            break
                    sl_from_entry = None
                    if coin_id:
                        atr_last = (tracker.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
                        coin_atr_params = tracker.atr_params_map.get(coin_id, tracker.atr_params)
                        if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                            sl_tmp, _tp_tmp = compute_stop_levels_atr(float(pos.entry_price), float(atr_last), coin_atr_params)
                            sl_from_entry = sl_tmp
                    if sl_from_entry is None:
                        sl_from_entry, _ = compute_stop_levels(float(pos.entry_price), tracker.risk)
                    entry_px = float(pos.entry_price)
                    risk_per_unit = max(1e-12, entry_px - float(sl_from_entry))
                    rr_unrealized = (float(current_price) - entry_px) / risk_per_unit
                    if rr_unrealized >= 1.0:
                        # Place/Update protective stop at entry (stop-limit a hair below)
                        limit_px = entry_px * 0.999
                        try:
                            ok = tracker.live_executor.place_stop_limit_sell(
                                symbol=tracker._symbol_to_market(sym),
                                quantity=float(pos.units),
                                stop_price=entry_px,
                                limit_price=limit_px,
                            )
                            if ok:
                                tracker._live_be_armed[sym] = True
                                log_event('live_be_armed', {
                                    'symbol': sym,
                                    'entry': entry_px,
                                    'stop_price': entry_px,
                                    'limit_price': limit_px,
                                    'rr_now': rr_unrealized,
                                })
                        except Exception as ex:
                            log_event('live_be_error', {'symbol': sym, 'error': str(ex)})
            except Exception:
                pass
            # Get ATR params and last ATR for this coin if available
            coin_id = None
            for cid, cfgc in tracker.config.tracked_coins.items():
                if cfgc.symbol.upper() == sym:
                    coin_id = cid
                    break
            coin_atr_params = tracker.atr_params_map.get(coin_id, tracker.atr_params)
            atr_last = None
            if coin_id is not None:
                atr_last = (tracker.history.get(coin_id, {}) or {}).get('last', {}).get('atr')
            # Compute SL/TP
            if (coin_atr_params is not None) and (atr_last is not None) and (float(atr_last) > 0):
                sl_from_entry, tp_from_entry = compute_stop_levels_atr(float(pos.entry_price), float(atr_last), coin_atr_params)
                if sl_from_entry is None or tp_from_entry is None:
                    sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), tracker.risk)
                trailing_level = compute_trailing_stop_atr(float(pos.peak_price), float(atr_last), coin_atr_params) or compute_trailing_stop(float(pos.peak_price), tracker.risk)
            else:
                sl_from_entry, tp_from_entry = compute_stop_levels(float(pos.entry_price), tracker.risk)
                trailing_level = compute_trailing_stop(float(pos.peak_price), tracker.risk)
            reason = None
            if float(current_price) <= float(sl_from_entry):
                reason = 'stop_loss'
            elif float(current_price) >= float(tp_from_entry):
                reason = 'take_profit'
            elif float(current_price) <= float(trailing_level):
                reason = 'trailing_stop'
            if reason is None:
                continue
            # Resolve market pair
            try:
                with open(tracker.config_path, 'r') as f:
                    cfg_all2 = yaml.safe_load(f) or {}
                per_coin = (cfg_all2.get('tracked_coins') or {}).get(coin_id) or {}
                market_pair = per_coin.get('market') or f"{sym}/USDT"
            except Exception:
                market_pair = f"{sym}/USDT"
            # Place market sell for full position value in USD
            try:
                size_usd = float(current_price) * float(pos.units)
                if size_usd <= 0:
                    continue
                live_order = tracker.live_executor.place_order(symbol=market_pair, side='sell', size_usd=size_usd, order_type='market')
                # Close position in portfolio at execution price
                exec_price = float(live_order.price or current_price)
                closed = tracker.portfolio.close(sym, price=exec_price)
                log_event('live_exit', {
                    'symbol': sym,
                    'market': market_pair,
                    'reason': reason,
                    'order_id': live_order.id,
                    'status': live_order.status,
                    'exit_price': exec_price,
                    'pnl_pct': (closed.get('pnl_pct') if closed else None),
                })
                try:
                    tracker.portfolio.save_state(tracker.state_path)
                except Exception:
                    pass
                # Persist trade in SQLite
                try:
                    if tracker.store is not None:
                        tracker.store.insert_trade({
                            'symbol': sym,
                            'market': market_pair,
                            'reason': reason,
                            'entry_price': float(closed.get('entry_price')) if closed else None,
                            'exit_price': exec_price,
                            'pnl_pct': (closed.get('pnl_pct') if closed else None),
                            'order_id': live_order.id,
                            'status': live_order.status,
                        })
                except Exception:
                    pass
                # reset backoff state on success
                try:
                    if sym in tracker._live_exit_backoff:
                        del tracker._live_exit_backoff[sym]
                except Exception:
                    pass
            except Exception as ex:
                log_event('live_exit_error', {'symbol': sym, 'reason': reason, 'error': str(ex)})
                # increase backoff for this symbol
                try:
                    st = tracker._live_exit_backoff.get(sym) or {"retries": 0.0, "next_ts": 0.0}
                    retries = float(st.get('retries', 0.0)) + 1.0
                    delay = min(60.0, max(2.0, 2.0 ** retries))
                    tracker._live_exit_backoff[sym] = {"retries": retries, "next_ts": time.time() + delay}
                    if delay >= 30.0:
                        log_event('live_backoff_alert', {'symbol': sym, 'reason': reason, 'delay_sec': delay})
                        try:
                            tracker.notifier.alert("Exit Backoff", f"{sym} delay {int(delay)}s (reason={reason})", style="yellow")
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        # Never raise from background manager
        pass
