# CairoGo Operations - Policy Notes

## The story
CairoGo is a ride-hailing app in Cairo (think Uber). A customer requests a ride and the system offers it to a nearby driver.
A request **fails** when it never becomes a trip: the driver rejects it, someone cancels it, or no driver is found (`request_failed = 1`). About one request in five fails.
The customer is left waiting. Many give up, ask for a refund, call support, or switch to another app.
The dispatch team can step in **before the trip**: call the customer, reassign to another driver, or offer an incentive. Each intervention is called a *review*.
Dispatch has people for only **15% of incoming requests**, so it cannot review all failures. Your model decides which requests get that attention.
A review costs a little dispatcher time. A failed request nobody reviewed costs about **4x** that (lost customer, refund, support call).

**Example.** Suppose CairoGo receives 1,000 requests. Dispatch can review only 15%, so it can review 150. If about 200 requests will fail, the goal is not to choose any 150 requests; it is to rank the requests so that as many likely failures as possible appear in those 150.

## Constraints
- Management can manually review only **15% of incoming requests**.
- A failed request that nobody reviewed costs about **4x** an unnecessary review.
- A driver incentive programme started during the data period (see `recent_labelled`). Nobody remembers the exact date.
- Zone names in the reference table were revised after the trips were logged.
- One pricing/measurement field changed unit on the same day a new app version rolled out.
- Anything recorded after a request is made is not available when the decision has to be taken.
- Interventions have a cost and a fixed budget of 3 EGP per incoming request. Management's assumed effect of each intervention is published in `DECISION_RULES.json` / `DECISION_NOTES.md` (common zip). These effects are assumptions, not measurements.
