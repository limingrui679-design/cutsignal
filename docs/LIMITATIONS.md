# Limitations and non-goals

## Not medical or nutrition care

CutSignal does not diagnose a plateau, eating disorder, endocrine condition, overtraining, injury,
or nutrient deficiency. It does not choose a safe calorie target, rate of weight loss, protein
target, sodium limit, or supplement. Those values are user inputs. Pain, dizziness, fainting,
rapid unexplained weight change, pregnancy, medication changes, or a history of disordered eating
require appropriate professional context rather than an automated plan adjustment.

## Model limitations

- Energy expenditure and intake are only partially identifiable from noisy weight observations.
- Food logging may be systematically biased; +10/+20% scenarios are examples, not corrections.
- Fluid, glycogen, sodium, menstrual-cycle, illness, medication, and travel effects are incompletely
  observed.
- The displayed recent-rate interval uses marginal state intervals and ignores temporal covariance.
- The state-space parameters are plausible defaults, not population-calibrated clinical priors.
- Change points describe a statistical segmentation and may lag the real event.

## Training limitations

- e1RM formulas assume consistent technique, equipment, range of motion, and effort.
- RPE is subjective; missing RPE widens only a heuristic uncertainty term.
- Shrinkage is empirical and can pull a real exercise-specific change toward the group median.
- A detected decline cannot distinguish energy deficit, program design, sleep, injury, or motivation.
- OpenPowerlifting is competition data and does not validate everyday training trends.

## Optimization limitations

- Food values are averages; recipes, cooking yield, label rounding, and portions vary.
- Box uncertainty protects against configured coefficient ranges only.
- The plan has no meal-timing, recipe-combination, inventory, seasonality, or food-safety model.
- A feasible incumbent may be returned at the time limit. Its MIP gap is displayed.
- Allergy tags and dietary labels are data fields, not guarantees against contamination.
- Prices and availability require local verification.

## Product non-goals

- No passive surveillance or always-on cloud sync.
- No universal “metabolic adaptation” diagnosis.
- No generated before/after claims.
- No automated calorie reduction based on one weigh-in.
- No native vendor API claim without a tested adapter and documented data contract.
