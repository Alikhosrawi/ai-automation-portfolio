# Supplies order for the week of Mon 19 Oct 2026: please check before checkout

Prepared Fri 16 Oct 2026, 17:00, from today's cupboard count and the 139 appointments booked for next week.

**Demo: nothing has been ordered.** The proposed carts (`2-proposed-cart-*.csv`) wait for your review. Only lines you approve go into the final cart.

## In the carts: 5 items from 3 suppliers
- Alster Example Praxisbedarf (fictional), arrives Mon 19 Oct: Kinesiology tape 5 cm x 5 m x 2 boxes of 6 rolls; Massage lotion 1 l x 1 bottle
- Elbe Example Hygiene (fictional), arrives Tue 20 Oct: Couch roll 50 m x 1 pack of 9 rolls; Surface disinfectant wipes x 1 case of 6 tubs
- Hafen Example Electro (fictional), arrives Wed 21 Oct: Electrode pads 5 x 5 cm x 2 boxes of 5 bags

## More than last week
- Kinesiology tape 5 cm x 5 m: 2 boxes of 6 rolls instead of 1, because 18 sports physio + taping sessions are booked next week vs 9 this week.
- Electrode pads 5 x 5 cm: 2 boxes of 5 bags instead of 1, because 16 electrotherapy sessions are booked next week vs 10 this week.

## Less than last week
- Rigid sports tape 3.8 cm: none this week (last week 1 box of 12 rolls). 16 rolls on the shelf cover the forecast of 11 + safety stock 4.
- Massage lotion 1 l: 1 bottle instead of 3, because there are still 2 bottles on the shelf (last Friday: 1).
- Ultrasound gel 250 ml: none this week (last week 1 case of 12 bottles). 13 bottles on the shelf cover the forecast of 3 + safety stock 3; 5 ultrasound sessions are booked next week vs 11 this week.
- Nitrile gloves, size M: none this week (last week 1 carton of 10 boxes). 8 boxes on the shelf cover the forecast of 3 + safety stock 3.
- Hand sanitiser 500 ml: none this week (last week 1 case of 10 bottles). 10 bottles on the shelf cover the forecast of 4 + safety stock 2.
- Paper hand towels: none this week (last week 1 carton of 20 bundles). 18 bundles on the shelf cover the forecast of 12 + safety stock 4.

## Same as last week
- Couch roll 50 m: 1 pack of 9 rolls, same as last week.
- Surface disinfectant wipes: 1 case of 6 tubs, same as last week.

## Not needed this week or last week
- Instant cold pack: nothing needed (14 cold packs on the shelf, forecast 6 + safety stock 6).

## Please check (a person should look at these)
- **Ultrasound gel 250 ml** (near expiry): 4 of the 13 bottles on the shelf are best before 20 Nov 2026. Use these first.
- **Nitrile gloves, size M** (stock dropped more than usage explains): 6 boxes went this week (last count 4 + delivered 10 - now 8), but this week's appointments explain about 2.2. Missing, miscounted, or moved to another room?
- **Electrode pads 5 x 5 cm** (may run short before the delivery): The order from Hafen Example Electro (fictional) arrives Wed 21 Oct (3 working days). Until then the bookings need about 5.2 bags, and only 3 bags are on the shelf.

## Next step: your review
Open `cart-review.csv`. For each line write **approve**, **change** (and the number of packs you want in approved_packs) or **remove** in the decision column, plus your name, the time and a short note. Then run **Build the approved cart**. Only approved lines go into the final cart. Lines to review this week: 5 waiting.

## How the numbers are made
Forecast = next week's bookings x how much each treatment uses x a correction learned from the last 8 weeks (general items like towels: the 4-week average, adjusted for how busy next week is). Order = forecast + safety stock - what is on the shelf - what is already in this week's cart, rounded up to whole packs. Every item with its numbers: `1-order-decisions.csv`.

_Wording: template text (AI drafting off)._
