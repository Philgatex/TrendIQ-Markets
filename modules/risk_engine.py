def calculate_position_size(
    account_equity: float,
    risk_percentage: float,
    entry_price: float,
    stop_loss_price: float,
    value_per_point: float = 1.0
) -> dict:
    if account_equity <= 0 or risk_percentage <= 0:
        return {
            "risk_amount": 0,
            "stop_distance": 0,
            "suggested_position_size": 0,
            "warning": "Enter valid account equity and risk percentage."
        }

    stop_distance = abs(entry_price - stop_loss_price)

    if stop_distance <= 0:
        return {
            "risk_amount": 0,
            "stop_distance": 0,
            "suggested_position_size": 0,
            "warning": "Stop-loss distance must be greater than zero."
        }

    risk_amount = account_equity * (risk_percentage / 100)
    suggested_position_size = risk_amount / (stop_distance * value_per_point)

    if risk_percentage > 5:
        warning = "Risk is high. Consider keeping risk below 1%–3% per trade."
    elif risk_percentage > 3:
        warning = "Risk is moderate-high. Use caution."
    else:
        warning = "Risk level is within a conservative range."

    return {
        "risk_amount": round(risk_amount, 2),
        "stop_distance": round(stop_distance, 4),
        "suggested_position_size": round(suggested_position_size, 4),
        "warning": warning
    }


def generate_trade_plan(
    direction: str,
    entry_price: float,
    stop_loss_price: float,
    account_equity: float,
    risk_percentage: float,
    value_per_point: float = 1.0
) -> dict:
    risk_data = calculate_position_size(
        account_equity,
        risk_percentage,
        entry_price,
        stop_loss_price,
        value_per_point
    )

    stop_distance = risk_data.get("stop_distance", 0)

    if direction.lower() == "buy":
        tp1 = entry_price + stop_distance
        tp2 = entry_price + (2 * stop_distance)
        tp3 = entry_price + (3 * stop_distance)
    else:
        tp1 = entry_price - stop_distance
        tp2 = entry_price - (2 * stop_distance)
        tp3 = entry_price - (3 * stop_distance)

    return {
        "direction": direction.upper(),
        "entry_price": round(entry_price, 4),
        "stop_loss_price": round(stop_loss_price, 4),
        "tp1": round(tp1, 4),
        "tp2": round(tp2, 4),
        "tp3": round(tp3, 4),
        "risk_reward_tp1": "1:1",
        "risk_reward_tp2": "1:2",
        "risk_reward_tp3": "1:3",
        **risk_data
    }
