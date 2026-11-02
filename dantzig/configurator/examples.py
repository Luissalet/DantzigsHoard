"""Sample catalogs bundled with the configurator (synthetic, for demos and tests)."""
from __future__ import annotations

from typing import Any


def drive_kit() -> dict[str, Any]:
    """Accionamiento industrial: motor, variador, red, fuente 24 V, armario, freno y ventilación.

    Includes a selection that needs two changes at once: motor 230 V, variador
    400 V y red 690 V (las tres tensiones deben coincidir).
    """
    def motor(i, label, kw, v, frame, price, stock=4):
        return {"id": i, "label": label, "price": price, "stock": stock,
                "attrs": {"kw": kw, "voltage": v, "frame": frame}}

    def drive(i, label, kw, v, aux, heat, price, stock=6):
        return {"id": i, "label": label, "price": price, "stock": stock,
                "attrs": {"max_kw": kw, "voltage": v, "aux_a": aux, "heat_w": heat}}

    return {
        "id": "drive-kit",
        "name": "Kit de accionamiento industrial",
        "currency": "EUR",
        "slots": [
            {"id": "motor", "label": "Motor", "required": True, "options": [
                motor("m075", "Motor 0,75 kW 230 V IEC80", 0.75, 230, 80, 180),
                motor("m15", "Motor 1,5 kW 400 V IEC90", 1.5, 400, 90, 260),
                motor("m30", "Motor 3 kW 400 V IEC100", 3, 400, 100, 390, stock=0),
                motor("m55", "Motor 5,5 kW 400 V IEC112", 5.5, 400, 112, 610),
                motor("m75h", "Motor 7,5 kW 690 V IEC132", 7.5, 690, 132, 820),
            ]},
            {"id": "drive", "label": "Variador", "required": True, "options": [
                drive("d1", "Variador 1 kW 230 V", 1, 230, 0.5, 40, 120),
                drive("d2", "Variador 2,2 kW 400 V", 2.2, 400, 0.8, 70, 210),
                drive("d4", "Variador 4 kW 400 V", 4, 400, 1.2, 120, 320),
                drive("d75", "Variador 7,5 kW 400 V", 7.5, 400, 1.5, 210, 470),
                drive("d75h", "Variador 7,5 kW 690 V", 7.5, 690, 1.5, 200, 520),
            ]},
            {"id": "grid", "label": "Conexión a red", "required": True, "options": [
                {"id": "g230", "label": "Monofásica 230 V", "price": 0, "attrs": {"voltage": 230}},
                {"id": "g400", "label": "Trifásica 400 V", "price": 45, "attrs": {"voltage": 400}},
                {"id": "g690", "label": "Trifásica 690 V", "price": 95, "attrs": {"voltage": 690}},
            ]},
            {"id": "psu", "label": "Fuente 24 V", "required": True, "options": [
                {"id": "p25", "label": "Fuente 24 V 2,5 A", "price": 35, "stock": 10, "attrs": {"current_a": 2.5}},
                {"id": "p5", "label": "Fuente 24 V 5 A", "price": 55, "stock": 10, "attrs": {"current_a": 5}},
                {"id": "p10", "label": "Fuente 24 V 10 A", "price": 90, "stock": 2, "attrs": {"current_a": 10}},
            ]},
            {"id": "enclosure", "label": "Armario", "required": True, "options": [
                {"id": "e_s", "label": "Armario pequeño IP54", "price": 140, "stock": 5, "attrs": {"max_frame": 90, "ip": 54}},
                {"id": "e_m", "label": "Armario mediano IP55", "price": 230, "stock": 5, "attrs": {"max_frame": 112, "ip": 55}},
                {"id": "e_l", "label": "Armario grande IP65", "price": 380, "stock": 3, "attrs": {"max_frame": 132, "ip": 65}},
            ]},
            {"id": "brake", "label": "Freno", "required": False, "options": [
                {"id": "b90", "label": "Freno hasta IEC90", "price": 75, "stock": 8, "attrs": {"max_frame": 90, "aux_a": 0.6}},
                {"id": "b132", "label": "Freno hasta IEC132", "price": 130, "stock": 8, "attrs": {"max_frame": 132, "aux_a": 1.0}},
            ]},
            {"id": "cooling", "label": "Ventilación", "required": False, "options": [
                {"id": "fan", "label": "Ventilador de armario", "price": 60, "stock": 12, "attrs": {"aux_a": 0.4}},
                {"id": "hex", "label": "Intercambiador de calor", "price": 210, "stock": 2, "attrs": {"aux_a": 0.9}},
            ]},
        ],
        "rules": [
            {"id": "power", "type": "compare", "label": "El variador debe cubrir la potencia del motor",
             "left": {"slot": "drive", "attr": "max_kw"}, "op": ">=", "right": {"slot": "motor", "attr": "kw"}},
            {"id": "volt_motor", "type": "compare", "label": "Motor y variador a la misma tensión",
             "left": {"slot": "drive", "attr": "voltage"}, "op": "==", "right": {"slot": "motor", "attr": "voltage"}},
            {"id": "volt_grid", "type": "compare", "label": "Variador y red a la misma tensión",
             "left": {"slot": "drive", "attr": "voltage"}, "op": "==", "right": {"slot": "grid", "attr": "voltage"}},
            {"id": "frame_fit", "type": "compare", "label": "El motor debe caber en el armario",
             "left": {"slot": "enclosure", "attr": "max_frame"}, "op": ">=", "right": {"slot": "motor", "attr": "frame"}},
            {"id": "brake_needed", "type": "requires", "label": "Motores de 3 kW o más llevan freno",
             "if": {"slot": "motor", "attr": "kw", "op": ">=", "value": 3}, "then": {"slot": "brake", "chosen": True}},
            {"id": "brake_frame", "type": "compare", "label": "El freno debe admitir el tamaño del motor",
             "left": {"slot": "brake", "attr": "max_frame"}, "op": ">=", "right": {"slot": "motor", "attr": "frame"}},
            {"id": "hot_drive", "type": "requires", "label": "Variadores de más de 100 W de pérdidas necesitan ventilación",
             "if": {"slot": "drive", "attr": "heat_w", "op": ">", "value": 100}, "then": {"slot": "cooling", "chosen": True}},
            {"id": "small_no_cooling", "type": "excludes", "label": "El armario pequeño no admite ventilación",
             "a": {"slot": "enclosure", "option": "e_s"}, "b": {"slot": "cooling", "chosen": True}},
            {"id": "hex_needs_large", "type": "requires", "label": "El intercambiador solo va en el armario grande",
             "if": {"slot": "cooling", "option": "hex"}, "then": {"slot": "enclosure", "option": "e_l"}},
            {"id": "big_drive_hex", "type": "requires", "label": "Variadores de 200 W o más de pérdidas necesitan intercambiador",
             "if": {"slot": "drive", "attr": "heat_w", "op": ">=", "value": 200}, "then": {"slot": "cooling", "option": "hex"}},
            {"id": "aux_budget", "type": "sum", "label": "Consumo de 24 V dentro de la fuente",
             "slots": ["drive", "brake", "cooling"], "attr": "aux_a", "op": "<=",
             "bound": {"slot": "psu", "attr": "current_a"}},
        ],
    }


CATALOGS = {"drive-kit": drive_kit}
