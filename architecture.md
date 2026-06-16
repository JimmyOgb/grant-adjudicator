# Architecture — Grant Adjudicator

## Storage: Single TreeMap Pattern

GenLayer only supports one TreeMap initialization per contract. All state uses prefixed string keys:

  "owner"        -> contract deployer address
  "count"        -> total grants created
  "grant:1"      -> JSON record for grant 1
  "grant:2"      -> JSON record for grant 2

## Execution Flow

submit_milestone() called
  |
  +-- Validate grant exists and status == "Active"
  +-- Update status to "Under Review", store submission URLs
  +-- Capture locals (milestone_desc, threshold, gh_url, dep_url)
  |
  +-- def run_evaluation() -> typing.Any:
          gl.nondet.web.render(gh_url, mode="text")[:2000]
          gl.nondet.web.render(dep_url, mode="text")[:2000]
          gl.nondet.exec_prompt(prompt)
          return json.loads(result)   <- parsed dict, not string
  |
  +-- gl.eq_principle.strict_eq(run_evaluation)
      All 5 nodes must return identical {vote, confidence, reasoning}
  |
  +-- if vote == "PASS" and confidence >= threshold:
          status = "Approved"
      else:
          status = "Rejected"

## Why Two Web Fetches in One Closure

Both the GitHub URL and deployment URL are fetched inside the SAME inner
function passed to strict_eq. This ensures all 5 validator nodes fetch
BOTH sources in the same execution context, preventing a scenario where
different nodes see different combinations of evidence.

## Type Constraints

  Class annotations : TreeMap[str, str] only
  Method parameters  : str, u256, bool        (NOT float, dict)
  Write returns      : typing.Any
  View returns        : str                    (NOT dict, list)

payout_amount and consensus_threshold are passed as str and cast to
float internally, since GenLayer write methods do not support float
parameters directly.

## Consensus vs Traditional Voting

Traditional DAO multisig: "3 of 5 signers approve" -- a tally.

GenLayer strict_eq: all 5 nodes must independently arrive at the SAME
verdict (vote, confidence, reasoning) for the transaction to succeed at
all. There is no partial-agreement state -- either consensus is reached
on one answer, or the transaction reverts and must be resubmitted.

## Owner-Gated Reset

reset_grant() checks str(gl.message.sender_address) against
state["owner"], and additionally requires the grant's current status
to be "Rejected" -- preventing resets of Active or Approved grants.
