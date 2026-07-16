"""Generate the sample Jensen troubleshooting manual PDF (a realistic test fixture).

This is a DEV tool, not part of the app. Regenerate with:
    pip install fpdf2
    python ingestion/sample_docs/generate_sample_manual.py

The committed PDF (jensen-washer-troubleshooting.pdf) is what `make ingest` reads. The content
is fictional but structured like a real service manual so retrieval + citations are meaningful.
"""

from pathlib import Path

from fpdf import FPDF

# Each entry becomes one page: (title, [paragraphs]).
SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Washer - Drum will not spin",
        [
            "SAFETY: Isolate the machine at the main disconnect and apply lockout/tagout before "
            "any inspection. Confirm the drum has fully stopped before opening the panel. Moving "
            "parts and residual voltage can cause serious injury.",
            "Step 1 - Door interlock. A failed door interlock reports as error code E14 and "
            "prevents the motor from energising. Verify interlock continuity and door strike "
            "alignment before anything else.",
            "Step 2 - Drive belt. Inspect the belt for wear, glazing, or slippage. Replace a "
            "cracked or glazed belt. Correct belt tension is 12 mm deflection at mid-span under "
            "light thumb pressure.",
            "Step 3 - Motor and inverter. If the interlock and belt are good, check the motor "
            "capacitor and the inverter output. Do not probe the inverter terminals while "
            "energised; use the service test point instead.",
        ],
    ),
    (
        "Washer - Will not fill or will not drain",
        [
            "SAFETY: Close the water supply before removing hoses. Standing water may be hot.",
            "No fill - Check the water inlet valve and the supply tap. Error code E18 indicates "
            "the fill timeout was exceeded. Clean the inlet filter screens.",
            "No drain - Error code E22 indicates water is not draining. Check the drain pump and "
            "hose for blockage, and clear the pump filter, before restarting a cycle.",
            "Overflow - Error code E27 indicates an overflow or a stuck pressure switch. Inspect "
            "the pressure hose for kinks and the air trap for debris.",
        ],
    ),
    (
        "Washer - Excessive vibration or walking",
        [
            "SAFETY: Never restrain a vibrating machine by hand. Stop the cycle first.",
            "Load - Uneven loads are the most common cause. Redistribute laundry and avoid single "
            "bulky items. The control aborts spin and shows E45 on repeated imbalance.",
            "Suspension - Inspect shock absorbers and suspension springs for wear. Replace "
            "absorbers in pairs.",
            "Levelling - Confirm all four feet are on the floor and the machine is level within "
            "2 mm. Tighten the locknuts after adjustment.",
        ],
    ),
    (
        "Error code quick reference",
        [
            "E14 - Door interlock open or faulty. Controller inhibits spin. Check interlock "
            "continuity and door strike alignment.",
            "E18 - Fill timeout. Water did not reach level in time. Check inlet valve, tap, and "
            "filter screens.",
            "E22 - Water not draining. Check drain pump and hose for blockage.",
            "E27 - Overflow or stuck pressure switch. Inspect pressure hose and air trap.",
            "E31 - Over-temperature on the heating circuit. Allow to cool and inspect the NTC "
            "sensor.",
            "E45 - Repeated spin imbalance. Redistribute the load; inspect suspension.",
            "E52 - Motor tacho signal lost. Check the tacho connector and motor wiring.",
        ],
    ),
    (
        "Dryer - No heat or overheating",
        [
            "SAFETY: Dryers reach high temperatures. Allow the cabinet to cool and isolate power "
            "before servicing. Clean lint before every inspection - lint is a fire hazard.",
            "No heat - Check the heating element, the thermal fuse, and the gas valve (gas "
            "models). A blown thermal fuse usually indicates restricted airflow.",
            "Overheating - Error code E31 indicates over-temperature. Inspect the NTC temperature "
            "sensor and the high-limit thermostat. Verify the exhaust duct is not blocked and the "
            "lint filter is clean.",
            "Airflow - Restricted airflow is the root cause of most heat faults. Check the lint "
            "screen, blower wheel, and exhaust run for blockage.",
        ],
    ),
    (
        "Dryer - Drum not turning",
        [
            "SAFETY: Confirm the drum has stopped and isolate power before opening the cabinet.",
            "Belt - A snapped or stretched drum belt is the most common cause. Replace the belt "
            "and inspect the idler pulley for free rotation.",
            "Motor - If the belt is intact, check the drive motor and its start capacitor. A "
            "humming motor that will not start often indicates a failed capacitor.",
        ],
    ),
    (
        "Ironer and flatwork - Steam valve maintenance",
        [
            "SAFETY: Steam lines operate at high temperature and pressure. Close the steam supply "
            "and allow the line to cool before servicing. Wear heat-resistant gloves.",
            "Leaking valve - A leaking steam valve is usually caused by a worn seat or diaphragm. "
            "Replace the diaphragm kit; the part reference varies by model, so confirm it against "
            "the parts list.",
            "Testing - After reassembly, pressure-test the valve at working pressure and check for "
            "leaks while restoring the supply slowly.",
            "Temperature - If the roll temperature is unstable, inspect the steam trap and the "
            "condensate return before suspecting the controller.",
        ],
    ),
    (
        "Electrical safety and lockout/tagout",
        [
            "Always assume circuits are live until proven otherwise. Isolate at the main "
            "disconnect, apply your personal lock and tag, and verify zero energy with a meter "
            "before touching terminals.",
            "Capacitors can hold a charge after power is removed. Discharge motor-run and inverter "
            "capacitors through a suitable resistor before handling.",
            "Never bypass a door interlock or a thermal safety device to keep a machine running. "
            "Report and replace failed safety components.",
        ],
    ),
    (
        "Preventive maintenance schedule",
        [
            "Daily - Clean lint filters on dryers. Wipe door seals and check for foreign objects "
            "in drums.",
            "Weekly - Inspect drive belts for wear and correct tension (washer belt: 12 mm "
            "mid-span deflection). Check hoses and clamps for leaks.",
            "Monthly - Clean drain pump filters, inspect suspension and shock absorbers, and "
            "verify machine levelling. Test door interlocks for correct operation.",
            "Quarterly - Inspect steam valves and traps, check electrical terminals for "
            "tightness, and review error-code history for recurring faults.",
        ],
    ),
]


def build(out_path: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for title, paras in SECTIONS:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        pdf.multi_cell(0, 9, title)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        for para in paras:
            pdf.multi_cell(0, 6.5, para)
            pdf.ln(1.5)
    pdf.output(str(out_path))
    print(f"wrote {out_path} ({len(SECTIONS)} pages)")


if __name__ == "__main__":
    build(Path(__file__).with_name("jensen-washer-troubleshooting.pdf"))
