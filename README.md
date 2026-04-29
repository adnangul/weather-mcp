# Weather MCP Server

The Weather MCP server exposes weather-related capabilities as Model Context Protocol (MCP) tools over HTTP. It allows programmatic access to real-time weather forecasts and weather alerts sourced from the US National Weather Service (NWS).

**Capabilities:**
- **Get Weather Alerts:** Retrieve active weather alerts for any US state (specified by two-letter code, e.g., CA, NY). Returns event type, affected area, severity, and recommended instructions.
- **Get Forecast:** Fetch detailed weather forecasts for a specific latitude and longitude. Returns the latest NWS forecast periods suitable for US locations.
- **Combined Alerts and Forecast:** Get a summary briefing combining state-wide alerts and a point-specific forecast for holistic planning and situational awareness.

All interactions are exposed as standardized MCP tools, making them suitable for integration with MCP clients, chaining, or use in Model Context Protocol inspectors.

The server is designed to run locally, in containers, or in cloud environments, and supports customization via environment variables for host and port configuration.

Google Cloud MCP servers overview - useful info regarding google hosted/maanged MCP servers 
https://docs.cloud.google.com/mcp/overview


Below instructions are targetted for GCP enviornment, make sure your executing it on shell already authenticated
If not, 
  gcloud auth login
  gcloud config set project <project id> 

  gcloud auth application-default login

Ensure $PROJECT_ID and LOCATION is set, if not
  export PROJECT_ID=ai-ml-team-sandbox
  export LOCATION=us-central1

---------------------
Deploy on Cloud Run
---------------------

Ensure $PROJECT_ID is set

1. create artifact registry (one time)

  gcloud artifacts repositories create remote-mcp-servers \
    --repository-format=docker \
    --location=$LOCATION \
    --description="Repository for remote MCP servers" \
    --project=$PROJECT_ID

2. build container image

  gcloud builds submit --region=$LOCATION --tag $LOCATION-docker.pkg.dev/$PROJECT_ID/remote-mcp-servers/mcp-server:latest


3. deploy, it will output the access url

  gcloud run deploy mcp-server \
    --image $LOCATION-docker.pkg.dev/$PROJECT_ID/remote-mcp-servers/mcp-server:latest \
    --region=$LOCATION \
    --no-allow-unauthenticated


- The above will secure the access to the mcp server via IAP, use 
  Note: --no-allow-unauthenticated will not allow request without authentication. It will requied this role (roles/run.invoker) to allow access

- We may use --allow-unauthenticated for dev or initial deployment for testing

  refer -
  https://cloud.google.com/blog/topics/developers-practitioners/build-and-deploy-a-remote-mcp-server-to-google-cloud-run-in-under-10-minutes

------------------------------------
Test using mcp inspector (optional)
------------------------------------
Simple
npx @modelcontextprotocol/inspector@latest

---------------------------------
Registering to cloud api registry
----------------------------------

4. Register the mcp server to the Agent Registry - ensure the agent registry is enabled, and to have  Agent Registry Editor (roles/agentregistry.editor) on the project (or equivalent permissions)

From the directory that contains `toolspec.json` (this repo root), run following (replace the url from previous step, but make sure to keep /mcp,protocolBinding=JSONRPC at the end):

  gcloud alpha agent-registry services create weather-mcp \
    --project=$PROJECT_ID \       
    --location=global \                                          
    --display-name="Weather MCP" \                         
    --description="The Weather MCP service provides tools to get weather alerts for any state (two letters e.g., TX), forecast for a specific latitude and longitude" \
    --mcp-server-spec-type=tool-spec \
    --mcp-server-spec-content=toolspec.json \
    --interfaces=url=https://<url/server>/mcp,protocolBinding=JSONRPC


------------------------------
Verify registration - Optional 
------------------------------ 
- Getting list of server
  
  gcloud alpha agent-registry services list \
    --project=$PROJECT_ID \
    --location=global

- get the details

  gcloud alpha agent-registry mcp-servers search \
    --project=$PROJECT_ID \
    --location=global \
    --search-string="weather-mcp"


------------------------------ 
references
------------------------------ 

- https://cloud.google.com/blog/topics/developers-practitioners/build-and-deploy-a-remote-mcp-server-to-google-cloud-run-in-under-10-minutes

- https://docs.cloud.google.com/run/docs/use-cloud-run-mcp
