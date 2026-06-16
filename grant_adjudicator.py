# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import json
import typing


class GrantAdjudicator(gl.Contract):
    # Single TreeMap — keys are prefixed strings:
    #   "owner"          -> contract owner address
    #   "count"          -> total grants created (str int)
    #   "grant:{id}"     -> JSON grant metadata + evaluation report
    state: TreeMap[str, str]

    def __init__(self):
        self.state = TreeMap()
        self.state["owner"] = str(gl.message.sender_address)
        self.state["count"] = "0"

    # ── helpers ────────────────────────────────────────────────────────

    def _count(self) -> int:
        return int(self.state["count"])

    def _grant_key(self, grant_id: int) -> str:
        return "grant:" + str(grant_id)

    def _grant_exists(self, grant_id: int) -> bool:
        return self._grant_key(grant_id) in self.state

    def _get_grant(self, grant_id: int) -> dict:
        k = self._grant_key(grant_id)
        if k not in self.state:
            raise Exception("Grant ID does not exist.")
        return json.loads(self.state[k])

    def _save_grant(self, grant_id: int, grant: dict) -> None:
        self.state[self._grant_key(grant_id)] = json.dumps(grant)

    # ── write methods ──────────────────────────────────────────────────

    @gl.public.write
    def create_grant(
        self,
        title: str,
        milestone_description: str,
        payout_amount: str,
        consensus_threshold: str,
    ) -> typing.Any:
        """
        Funding organization initializes a grant with clear milestone criteria.

        Args:
            title:                 Short grant title.
            milestone_description: Detailed requirements the grantee must fulfill.
            payout_amount:         Amount to pay on approval (as string, e.g. "5000").
            consensus_threshold:   Minimum confidence to approve, 0.0-1.0 (e.g. "0.70").

        Returns:
            The new grant's integer ID.
        """
        new_count  = self._count() + 1
        grant_id   = new_count
        creator    = str(gl.message.sender_address)

        grant = {
            "id":                    grant_id,
            "title":                 title,
            "milestone_description": milestone_description,
            "payout_amount":         payout_amount,
            "consensus_threshold":   consensus_threshold,
            "creator":               creator,
            "status":                "Active",
            "github_url":            "",
            "deployment_url":        "",
            "vote":                  "",
            "confidence":            "",
            "reasoning":             "",
            "evaluation_summary":    "",
        }

        self._save_grant(grant_id, grant)
        self.state["count"] = str(new_count)
        print("Grant #" + str(grant_id) + " created: " + title)
        return grant_id

    @gl.public.write
    def submit_milestone(
        self,
        grant_id: u256,
        github_url: str,
        deployment_url: str,
    ) -> typing.Any:
        """
        Grantee submits proof-of-work links. Contract immediately triggers
        AI consensus evaluation across 5 validator nodes.

        Args:
            grant_id:        The grant to submit against.
            github_url:      URL to the project's GitHub repository.
            deployment_url:  URL to the live deployed application.

        Returns:
            Evaluation result string with vote, confidence, and reasoning.
        """
        gid   = int(grant_id)
        grant = self._get_grant(gid)

        if grant["status"] != "Active":
            raise Exception(
                "Grant is not active. Current status: " + grant["status"]
            )

        # Record submission URLs
        grant["github_url"]    = github_url
        grant["deployment_url"] = deployment_url
        grant["status"]        = "Under Review"
        self._save_grant(gid, grant)

        # Capture locals for nondet closure
        milestone_desc = grant["milestone_description"]
        threshold      = float(grant["consensus_threshold"])
        gh_url         = github_url
        dep_url        = deployment_url

        def run_evaluation() -> typing.Any:
            # Fetch live evidence from both submitted URLs
            try:
                github_data = gl.nondet.web.render(gh_url, mode="text")[:2000]
            except Exception:
                github_data = "GitHub URL unavailable or private."

            try:
                deployment_data = gl.nondet.web.render(dep_url, mode="text")[:2000]
            except Exception:
                deployment_data = "Deployment URL unavailable."

            prompt = f"""
You are an expert technical auditor for a decentralized DAO grant program.
Objectively analyze the submitted project evidence against the milestone requirements.

[Milestone Requirements]:
{milestone_desc}

[GitHub Repository Content]:
{github_data}

[Live Deployment Content]:
{deployment_data}

Determine if the submission successfully meets ALL stated requirements.

Respond with the following JSON format:
{{
    "vote": str,          // "PASS" or "FAIL"
    "confidence": float,  // 0.0 to 1.0
    "reasoning": str      // detailed one-paragraph analysis
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
"""
            result = (
                gl.nondet.exec_prompt(prompt)
                .replace("```json", "")
                .replace("```", "")
            )
            print(result)
            return json.loads(result)

        evaluation = gl.eq_principle.strict_eq(run_evaluation)

        vote       = evaluation.get("vote", "FAIL")
        confidence = float(evaluation.get("confidence", 0.0))
        reasoning  = evaluation.get("reasoning", "")

        # Reload grant (state may have been read before nondet)
        grant = self._get_grant(gid)
        grant["vote"]       = vote
        grant["confidence"] = str(confidence)
        grant["reasoning"]  = reasoning

        if vote == "PASS" and confidence >= threshold:
            grant["status"] = "Approved"
            grant["evaluation_summary"] = (
                "Milestone APPROVED by AI consensus. "
                "Confidence: " + str(round(confidence * 100)) + "%. "
                "Payout of " + grant["payout_amount"] + " authorized."
            )
            self._save_grant(gid, grant)
            return (
                "Milestone Approved — confidence "
                + str(round(confidence * 100)) + "% >= threshold "
                + str(round(threshold * 100)) + "%. "
                "Payout of " + grant["payout_amount"] + " authorized. "
                "Reasoning: " + reasoning
            )
        else:
            grant["status"] = "Rejected"
            grant["evaluation_summary"] = (
                "Milestone REJECTED by AI consensus. "
                "Vote: " + vote + ". "
                "Confidence: " + str(round(confidence * 100)) + "%. "
                "Standards not met."
            )
            self._save_grant(gid, grant)
            return (
                "Milestone Rejected — vote: " + vote
                + ", confidence: " + str(round(confidence * 100)) + "%. "
                "Reasoning: " + reasoning
            )

    @gl.public.write
    def reset_grant(self, grant_id: u256) -> typing.Any:
        """
        Owner-only: reset a rejected grant back to Active so the grantee
        can resubmit after improvements.

        Args:
            grant_id: The grant to reset.
        """
        if str(gl.message.sender_address) != self.state["owner"]:
            raise Exception("Only the contract owner can reset grants.")

        gid   = int(grant_id)
        grant = self._get_grant(gid)

        if grant["status"] not in ["Rejected"]:
            raise Exception(
                "Only rejected grants can be reset. Status: " + grant["status"]
            )

        grant["status"]             = "Active"
        grant["github_url"]         = ""
        grant["deployment_url"]     = ""
        grant["vote"]               = ""
        grant["confidence"]         = ""
        grant["reasoning"]          = ""
        grant["evaluation_summary"] = ""
        self._save_grant(gid, grant)

        return "Grant #" + str(gid) + " reset to Active for resubmission."

    # ── view methods ───────────────────────────────────────────────────

    @gl.public.view
    def get_grant_status(self, grant_id: u256) -> str:
        """Returns the full grant record as a JSON string."""
        gid = int(grant_id)
        if not self._grant_exists(gid):
            return '{"error": "Grant not found."}'
        return self.state[self._grant_key(gid)]

    @gl.public.view
    def get_grant_summary(self, grant_id: u256) -> str:
        """Returns a quick human-readable summary of a grant's status."""
        gid = int(grant_id)
        if not self._grant_exists(gid):
            return "Grant not found."
        grant = self._get_grant(gid)
        return (
            "Grant #" + str(gid)
            + " — " + grant["title"]
            + " | Status: " + grant["status"]
            + " | Payout: " + grant["payout_amount"]
            + " | " + grant["evaluation_summary"]
        )

    @gl.public.view
    def get_total_grants(self) -> str:
        """Returns the total number of grants created."""
        return self.state["count"]

    @gl.public.view
    def get_owner(self) -> str:
        """Returns the contract owner address."""
        return self.state["owner"]
