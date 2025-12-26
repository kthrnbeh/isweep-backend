def decide(event: Event) -> DecisionResponse:
    """
    The CORE of ISweep:
    Given an Event, return a DecisionResponse telling the frontend:
       - what action to take
       - how long
       - whether to show the broom icon
       - the reason (for logs/UI)

    Steps performed:
      1. Build a default decision (do nothing)
      2. Check for manual override
      3. Try to infer content_type from subtitle text
      4. If still unknown, return "none"
      5. Enforce a confidence threshold
      6. Look up user preference for that content type
      7. If preference exists → apply it
      8. Return final decision
    """

    # ---------------------------------------------
    # 1. Default decision (nothing happens)
    # ---------------------------------------------
    decision = DecisionResponse(
        action=Action.none,
        duration_seconds=None,
        show_icon=False,
        reason="No matching preference or low confidence.",
    )

    # ---------------------------------------------
    # 2. Manual override
    # ---------------------------------------------
    # If the frontend sets event.manual_override = True,
    # this means the user pressed a remote button such as:
    #    "Skip this now"
    # regardless of AI detection.
    if event.manual_override:
        decision.action = Action.skip
        decision.duration_seconds = 10.0
        decision.show_icon = True
        decision.reason = "Manual override from user."
        return decision

    # ---------------------------------------------
    # 3. Infer content_type (if needed)
    # ---------------------------------------------
    _infer_content_type_from_text(event)

    # ---------------------------------------------
    # 4. If still no content type, can't apply rules
    # ---------------------------------------------
    if not event.content_type:
        decision.reason = "No content_type provided or inferred."
        return decision

    # ---------------------------------------------
    # 5. Confidence threshold
    # ---------------------------------------------
    # Once you integrate AI models:
    #   confidence < 0.75 means the model is unsure.
    if event.confidence is not None and event.confidence < 0.75:
        decision.reason = f"Confidence {event.confidence} below threshold."
        return decision

    # ---------------------------------------------
    # 6. Look up user preference for this category
    # ---------------------------------------------
    pref = get_preference(event.user_id, event.content_type.value)
    if not pref or not pref.enabled:
        # User disabled this filter or doesn't have one
        decision.reason = "No enabled preference for this content type."
        return decision

    # ---------------------------------------------
    # 7. Apply user's preferred action
    # ---------------------------------------------
    decision.action = pref.action
    decision.duration_seconds = pref.duration_seconds
    decision.show_icon = True
    decision.reason = f"Matched preference for {event.content_type.value}."

    # ---------------------------------------------
    # 8. Return final action
    # ---------------------------------------------
    return decision
