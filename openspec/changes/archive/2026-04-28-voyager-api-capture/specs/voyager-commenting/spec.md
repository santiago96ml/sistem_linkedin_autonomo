# Voyager Commenting Specification

## Purpose
Define the requirements for submitting comments to LinkedIn using the Voyager GraphQL API.

## Requirements

### Requirement: GraphQL Comment Submission
The system MUST submit comments via the `https://www.linkedin.com/voyager/api/graphql` endpoint using a POST request.

#### Scenario: Successful Comment
- GIVEN a valid post URN and comment text
- WHEN the system sends a POST request with `queryId: voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87` and `action: execute`
- THEN the response SHOULD indicate success (Status 200/201)

### Requirement: Authentication Headers
The system MUST include mandatory headers to authenticate the GraphQL request.
- `csrf-token`: MUST match the `JSESSIONID` cookie value.
- `x-restli-protocol-version`: MUST be `2.0.0`.
- `x-li-track`: MUST contain valid Base64 encoded client metadata.

#### Scenario: Unauthorized Comment
- GIVEN an invalid or missing `csrf-token`
- WHEN the system attempts to submit a comment
- THEN the API MUST reject the request with a 401/403 status
