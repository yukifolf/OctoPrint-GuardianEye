"""
Stage-Aware Vision Prompt Builder for GuardianEye.

Generates the system prompt sent to AI vision providers. The prompt is
carefully tuned to minimize false positives (the "poop test" — pre-existing
debris on the bed should never trigger a failure).

Ported from bambu-lab-mcp/src/print-monitor.ts:buildVisionPrompt(),
generalized for any printer/camera setup.
"""

_DEFAULT_PROMPT = """You are an expert 3D print failure detector. You are analyzing a camera frame from a 3D printer's webcam to evaluate the state of the active print.

PRINTER CONTEXT:
- Camera: fixed webcam pointed at the build area
- Build plate: may have glue residue, tape, bed markings, or surface texture — this is NORMAL
- The toolhead / extruder moves fast and may appear blurred — this is NORMAL

{stage_context}

NORMAL FEATURES — do NOT flag as failure:
- Purge lines along the edge of the bed, purge blobs, or prime/wipe towers
- Skirt or brim outlines printed around the base of the model
- Thin, sparse first layers during early stages
- Motion blur of the moving toolhead, extruder, or gantry
- Minor stringing (fine hair-like wisps between parts) that does not disrupt model structure
- Objects that look short/flat because the print is still in early layers

FAILURE SIGNS — FLAG AS FAIL if any of these are visible:
- Spaghetti: loose, tangled, chaotic nest of filament noodles anywhere on the bed, around the model, or falling off the plate.
- Detachment: the printed model has detached from the build plate, slid out of position, tipped over, or is being dragged by the nozzle.
- Severe Warping: the base or corners of the printed model have severely curled or peeled upward off the build plate.
- Layer Shifting: noticeable horizontal displacement or staircase-like misalignment between stacked layers of the object.
- Printing into Air: the nozzle is extruding in mid-air above the model with nothing beneath it, or the model stopped growing while the head moves above it.
- Model Collapse / Destruction: broken walls, collapsed infill, shattered geometry, or massive clumps/blobs of plastic engulfing the nozzle or print.

DECISION GUIDELINES:
1. Examine the active 3D printed model on the build plate.
2. If the printed model is cleanly forming stacked layers and firmly adhering to the bed, it is OK.
3. If the model has detached, tipped over, shifted layers, or turned into spaghetti/loose filament, it is a FAIL.
4. Purge lines on the periphery are normal; chaos, detachment, or noodles in the active model area are NOT normal.

Respond in this format:
VERDICT: OK
or
VERDICT: FAIL | <concise failure reason>"""


def _build_stage_context(layer, total_layers, progress):
    """Generate stage-specific context for the vision prompt."""
    total_str = str(total_layers) if total_layers else "?"
    early = layer is not None and layer <= 5
    late = progress is not None and progress >= 80

    if early:
        return (
            f"STAGE: Early print (layer {layer}/{total_str}, {progress or 0}%). "
            "Only initial base layers, skirts, or brim are on the bed. "
            "Ensure the first layers are sticking flatly to the bed without peeling, bunching, or dragging."
        )
    elif late:
        return (
            f"STAGE: Late print (layer {layer}/{total_str}, {progress or 0}%). "
            "The 3D printed model should be tall and nearly complete with defined shape. "
            "Check for layer shifts, top surface collapse, or detachment caused by leverage."
        )
    else:
        return (
            f"STAGE: Mid print (layer {layer or '?'}/{total_str}, {progress or 0}%). "
            "The 3D printed model should have visible vertical height with stacked layers adhering firmly to the bed. "
            "Check for spaghetti, detachment, warping, or layer shifts."
        )


def build_vision_prompt(layer=None, total_layers=None, progress=None, custom_prompt=None):
    """
    Build the complete vision analysis prompt.

    Args:
        layer: Current layer number (None if unknown)
        total_layers: Total layers in the print (None if unknown)
        progress: Print progress 0-100 (None if unknown)
        custom_prompt: User override prompt (uses default if empty/None)

    Returns:
        Complete prompt string with stage context interpolated.
    """
    stage_context = _build_stage_context(layer, total_layers, progress)
    template = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else _DEFAULT_PROMPT
    return template.replace("{stage_context}", stage_context)
