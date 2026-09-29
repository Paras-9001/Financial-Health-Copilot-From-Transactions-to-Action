# Phase 7 Implementation

Phase 7 follows `IMPLEMENTATION_PLAN.md` and completes the integration layer on top of the cumulative Phase 0–6 application.

## Delivered

- Real backend contracts are used by every frontend route.
- New checking/savings transactions update the current account balance; credit-card activity follows liability balance semantics.
- Medical, hospital, and pharmacy descriptions map deterministically to Healthcare.
- A shared recalculation controller captures financial state before a data mutation, reruns summary/risk/recommendation queries afterward, invalidates every dependent React Query cache, and computes a user-facing diff.
- `<RecalculationToast>` shows the mutation cause, changed expenses and cash buffer, new/resolved risks, and top-recommendation changes, with a direct link to Recommendations.
- Direct transaction entry, manual onboarding transaction entry, CSV confirmation, and category corrections all use the recalculation workflow.
- Loading, retry, disabled, and mutation-progress states use consistent query defaults and existing accessible state components.

## Scenario 7

The exact authoritative scenario is covered by `backend/tests/test_phase7.py` and `frontend/tests/phase7-recalculation.spec.ts`: seed Ananya, add a ₹12,000 medical debit, verify the checking balance changes from ₹9,000 to -₹3,000, and verify summary, risks, and recommendations change.

## Boundaries

Phase 8 owns expansion of the complete automated suite. Phase 9 owns the one-click demo injector and presentation polish; Phase 7 deliberately uses the normal Add Transaction flow.
