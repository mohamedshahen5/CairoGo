# Data dictionary - CairoGo Operations Pack
`recorded_at` tells you WHEN each column becomes known: at_request / after_decision / after_acceptance / after_completion.

| column | table | recorded_at |
|---|---|---|
| trip_id | trips | at_request |
| customer_id | trips | at_request |
| driver_id | trips | at_request |
| request_ts | trips | at_request |
| pickup_zone | trips | at_request |
| dropoff_zone | trips | at_request |
| distance_km | trips | at_request |
| surge_multiplier | trips | at_request |
| est_fare | trips | at_request |
| eta_estimate_min | trips | at_request |
| weather | trips | at_request |
| payment_method | trips | at_request |
| service_level | trips | at_request |
| request_failed | trips | outcome (target 1: 1 = driver rejected / cancelled / no driver) |
| actual_trip_time_min | trips | after_completion (target 2; empty when the trip did not happen) |
| cancel_reason | trips | after_decision |
| fare_final | trips | after_completion |
| support_ticket_flag | trips | after_completion |

Other tables: `zones`, `drivers`, `customers`. `rating_avg` is empty for drivers without enough rated trips.
