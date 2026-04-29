# Voyager Reactions Specification

## Purpose
Define the requirements for submitting post reactions (likes) to LinkedIn using the Voyager GraphQL API.

## Requirements

### Requirement: GraphQL Reaction Submission
The system MUST submit reactions via the `https://www.linkedin.com/voyager/api/graphql` endpoint.

#### Scenario: Successful Reaction (Like)
- GIVEN a valid post URN and reaction type 'LIKE'
- WHEN the system sends a POST request with `queryId: voyagerSocialDashReactions.b731222600772fd42464c0fe19bd722b` and `action: execute`
- THEN the response SHOULD indicate success
