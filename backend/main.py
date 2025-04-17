import asyncio
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, HttpUrl
import random # Added for simulation
import requests # Added for actual test
import ssl # Added for potential cert checks (more advanced)
from urllib.parse import urlparse # Added for URL parsing

import database
import models

# --- Pydantic Schemas ---

class WebsiteBase(BaseModel):
    url: HttpUrl

class WebsiteCreate(WebsiteBase):
    pass

class WebsiteResponse(WebsiteBase):
    id: int
    created_at: datetime.datetime
    last_scan_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True # Kept for potential compatibility, use from_attributes in Pydantic v2
        from_attributes = True # Pydantic v2 way

class TestDefinitionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class ScanResultBase(BaseModel):
    status: models.TestStatusEnum
    result: models.TestResultEnum
    summary: Optional[str] = None
    details: Optional[str] = None
    recommendations: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None

class ScanResultResponse(ScanResultBase):
    id: int
    test_definition: TestDefinitionResponse # Nested response model

    class Config:
        from_attributes = True

class ScanBase(BaseModel):
    status: models.TestStatusEnum

class ScanResponse(ScanBase):
    id: int
    website: WebsiteResponse # Nested response model
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None
    results: List[ScanResultResponse] = []

    class Config:
        from_attributes = True

class ScanRequest(BaseModel):
    url: HttpUrl

# --- FastAPI App Setup ---

app = FastAPI(title="Penetration Testing API")

# CORS Configuration
origins = [
    "http://localhost:3000",  # Allow Next.js dev server
    # Add other origins if needed (e.g., your deployed frontend URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Event Handlers ---

@app.on_event("startup")
async def on_startup():
    """Initialize database and populate initial test definitions."""
    print("Initializing database...")
    await database.init_db()
    print("Database initialized.")
    await populate_test_definitions()
    print("Test definitions populated.")


async def populate_test_definitions():
    """Adds the predefined tests to the database if they don't exist."""
    async with database.AsyncSessionLocal() as session:
        async with session.begin():
            test_defs = [
                {"name": "Vulnerability Scanning", "description": "General vulnerability checks (e.g., outdated software)."},
                {"name": "Web Application Firewall (WAF) Testing", "description": "Testing WAF detection and bypass."},
                {"name": "Cross-Site Scripting (XSS) Testing", "description": "Detecting XSS vulnerabilities."},
                {"name": "SQL Injection Testing", "description": "Detecting SQL Injection vulnerabilities."},
                {"name": "Denial of Service (DoS) Testing", "description": "Basic DoS resilience checks."},
                {"name": "Directory Traversal", "description": "Checking for directory traversal vulnerabilities."},
                {"name": "API Security Testing", "description": "Basic checks for common API vulnerabilities."},
                {"name": "Session Management Testing", "description": "Analyzing session handling security."},
                {"name": "Cryptography and SSL/TLS Testing", "description": "Checking SSL/TLS configuration and certificate validity."},
                {"name": "Social Engineering Testing", "description": "Placeholder for social engineering test info."},
                # {"name": "Mobile App Penetration Testing", "description": "Placeholder for mobile testing."}, # Optional
            ]

            for test_data in test_defs:
                stmt = select(models.TestDefinition).filter_by(name=test_data["name"])
                result = await session.execute(stmt)
                existing_test = result.scalars().first()
                if not existing_test:
                    new_test = models.TestDefinition(**test_data)
                    session.add(new_test)
            # No need to commit here, handled by 'async with session.begin()'


# --- Test Functions ---

async def run_single_test(scan_result_id: int, url: str):
    """Runs a single test and updates its status in the database."""
    # Use a separate session for each test run to isolate transactions
    async with database.AsyncSessionLocal() as session:
        # 1. Fetch Test Details and Mark as In Progress
        test_name = None
        try:
            async with session.begin():
                stmt = select(models.ScanResult).where(models.ScanResult.id == scan_result_id).options(selectinload(models.ScanResult.test_definition))
                result = await session.execute(stmt)
                scan_result = result.scalars().first()

                if not scan_result or not scan_result.test_definition:
                    print(f"Error: ScanResult or TestDefinition not found for id {scan_result_id}.")
                    return # Cannot proceed

                test_name = scan_result.test_definition.name
                print(f"Starting test '{test_name}' for URL: {url} (ScanResult ID: {scan_result_id})")

                scan_result.status = models.TestStatusEnum.IN_PROGRESS
                scan_result.started_at = datetime.datetime.now(datetime.timezone.utc)
                # Commit happens automatically via 'async with session.begin()'
        except Exception as e:
            print(f"Error updating status to IN_PROGRESS for test {scan_result_id}: {e}")
            # Consider how to handle this - maybe update status to ERROR in a separate transaction?
            return # Exit if we can't even mark it as started

        # 2. Execute the Actual Test Logic
        outcome = models.TestResultEnum.NOT_RUN
        summary_text = f"{test_name} did not complete."
        details_text = None
        recommendations_text = None
        final_status = models.TestStatusEnum.ERROR # Default to error unless successful

        try:
            if test_name == "Cryptography and SSL/TLS Testing":
                print(f"Running actual SSL/TLS check for {url}")
                try:
                    # Use a timeout, allow redirects, verify SSL certs by default
                    # Consider adding custom headers if needed (e.g., User-Agent)
                    headers = {'User-Agent': 'PenTestApp/1.0'}
                    response = requests.get(url, timeout=10, allow_redirects=True, verify=True, headers=headers)
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                    final_url = response.url
                    parsed_final_url = urlparse(final_url)

                    if parsed_final_url.scheme == "https":
                        outcome = models.TestResultEnum.PASSED
                        summary_text = "Website uses HTTPS."
                        details_text = f"The final URL ({final_url}) is served over HTTPS."
                        recommendations_text = "Ensure HTTPS is enforced (e.g., via HSTS) and uses modern TLS protocols/ciphers (requires deeper scan)."
                    else:
                        outcome = models.TestResultEnum.VULNERABLE # Treat non-HTTPS as vulnerable
                        summary_text = "Website does not enforce HTTPS."
                        details_text = f"The final URL ({final_url}) is served over HTTP, which is insecure."
                        recommendations_text = "Migrate the website to HTTPS and configure redirection from HTTP to HTTPS. Implement HSTS."

                    final_status = models.TestStatusEnum.COMPLETED

                except requests.exceptions.SSLError as ssl_err:
                    outcome = models.TestResultEnum.VULNERABLE
                    summary_text = "SSL/TLS Certificate Error."
                    details_text = f"An SSL error occurred: {str(ssl_err)}. This could indicate an invalid, expired, self-signed, or misconfigured certificate."
                    recommendations_text = "Review the SSL/TLS certificate configuration on the server. Ensure it's valid, trusted, covers the correct domain(s), and is correctly installed with the full chain."
                    final_status = models.TestStatusEnum.COMPLETED # Test completed, but found an issue
                except requests.exceptions.Timeout:
                    outcome = models.TestResultEnum.INFO # Treat timeout as informational
                    summary_text = "Request Timed Out."
                    details_text = f"The request to {url} timed out after 10 seconds."
                    recommendations_text = "Check server availability and network connectivity. The server might be slow, unresponsive, or firewalled."
                    final_status = models.TestStatusEnum.COMPLETED # Test completed, but couldn't get result
                except requests.exceptions.ConnectionError as conn_err:
                    outcome = models.TestResultEnum.INFO
                    summary_text = "Connection Error."
                    details_text = f"Could not connect to {url}. Error: {str(conn_err)}"
                    recommendations_text = "Verify the domain name resolves correctly and the server is reachable on the expected port (80/443)."
                    final_status = models.TestStatusEnum.COMPLETED # Test completed, but couldn't connect
                except requests.exceptions.RequestException as req_err:
                    outcome = models.TestResultEnum.INFO # General request error
                    summary_text = "Request Error."
                    details_text = f"An error occurred during the request: {str(req_err)}"
                    recommendations_text = "Check the URL for correctness and ensure the website is accessible. Review server logs if possible."
                    final_status = models.TestStatusEnum.COMPLETED # Test completed, but request failed

            # --- Add other test implementations here ---
            # elif test_name == "Cross-Site Scripting (XSS) Testing":
            #     # ... XSS test logic using requests/BeautifulSoup ...
            #     pass
            # elif test_name == "SQL Injection Testing":
            #     # ... SQLi test logic (careful with this!) ...
            #     pass

            else:
                # Simulate other tests for now
                print(f"Simulating test '{test_name}' for {url}")
                await asyncio.sleep(random.uniform(0.5, 2.5)) # Shorter simulation time
                outcome = random.choice([models.TestResultEnum.PASSED, models.TestResultEnum.VULNERABLE, models.TestResultEnum.INFO])
                summary_text = f"{test_name} completed (simulated)."
                details_text = f"Simulated details for {test_name} on {url}."
                recommendations_text = f"Simulated recommendations for {test_name}."
                final_status = models.TestStatusEnum.COMPLETED

        except Exception as e:
            # Catch unexpected errors during the *specific test logic*
            print(f"Unexpected error during test '{test_name}' execution for {url}: {e}")
            final_status = models.TestStatusEnum.ERROR
            outcome = models.TestResultEnum.NOT_RUN # Result is unknown due to error
            summary_text = f"An unexpected error occurred during the {test_name} test execution."
            details_text = f"Error details: {str(e)}"


        # 3. Update Database with Final Results
        try:
            async with session.begin():
                # Fetch the scan_result again within the same session
                # (SQLAlchemy manages object state within the session)
                stmt_update = select(models.ScanResult).where(models.ScanResult.id == scan_result_id)
                result_update = await session.execute(stmt_update)
                scan_result_update = result_update.scalars().first()

                if scan_result_update:
                    scan_result_update.status = final_status
                    scan_result_update.result = outcome
                    scan_result_update.summary = summary_text
                    scan_result_update.details = details_text
                    scan_result_update.recommendations = recommendations_text
                    scan_result_update.completed_at = datetime.datetime.now(datetime.timezone.utc)
                    print(f"Finished test '{test_name}' for URL: {url} with status: {final_status.value}, result: {outcome.value}")
                else:
                     # This shouldn't happen if the initial fetch worked, but good to log
                     print(f"Error: ScanResult with id {scan_result_id} not found for final update.")
                # Commit happens automatically
        except Exception as e:
            print(f"Error updating final status for test {scan_result_id}: {e}")
            # The status might remain IN_PROGRESS if this fails


async def run_all_tests_for_scan(scan_id: int, url: str):
    """Runs all tests associated with a scan concurrently."""
    print(f"Starting all tests for Scan ID: {scan_id}, URL: {url}")
    tasks = []
    scan_result_ids = []

    # Fetch all ScanResult IDs for the given Scan ID in a separate session
    async with database.AsyncSessionLocal() as session:
        try:
            stmt = select(models.ScanResult.id).where(models.ScanResult.scan_id == scan_id)
            result = await session.execute(stmt)
            scan_result_ids = result.scalars().all()
        except Exception as e:
            print(f"Error fetching scan result IDs for scan {scan_id}: {e}")
            # Need to update the main scan status to ERROR here
            async with database.AsyncSessionLocal() as error_session:
                async with error_session.begin():
                    stmt_err = select(models.Scan).where(models.Scan.id == scan_id)
                    res_err = await error_session.execute(stmt_err)
                    scan_err = res_err.scalars().first()
                    if scan_err:
                        scan_err.status = models.TestStatusEnum.ERROR
                        scan_err.completed_at = datetime.datetime.now(datetime.timezone.utc)
            return # Stop processing if we can't get the tests

    if not scan_result_ids:
        print(f"No tests found for Scan ID: {scan_id}. Marking scan as completed (or error?).")
         # Decide if no tests means completed or error state for the main scan
        async with database.AsyncSessionLocal() as final_session:
             async with final_session.begin():
                stmt = select(models.Scan).where(models.Scan.id == scan_id)
                result = await final_session.execute(stmt)
                scan = result.scalars().first()
                if scan and scan.status == models.TestStatusEnum.PENDING: # Only update if still pending
                    scan.status = models.TestStatusEnum.COMPLETED # Or ERROR?
                    scan.completed_at = datetime.datetime.now(datetime.timezone.utc)
        return

    # Create a task for each test using its ID
    for sr_id in scan_result_ids:
        tasks.append(asyncio.create_task(run_single_test(sr_id, url)))

    # Wait for all test tasks to complete
    if tasks:
        # Exceptions in tasks will propagate here if not caught within run_single_test
        # We wrap gather in a try/except block to ensure final status update happens
        try:
            await asyncio.gather(*tasks)
        except Exception as gather_err:
            print(f"Error during asyncio.gather for scan {scan_id}: {gather_err}")
            # Individual task errors should be handled within run_single_test,
            # but this catches errors from gather itself or unhandled task exceptions.

    # Final check and update of the main Scan status
    async with database.AsyncSessionLocal() as final_session:
        async with final_session.begin():
            # Re-fetch the scan and all its results to determine the final status
            stmt = select(models.Scan).where(models.Scan.id == scan_id).options(selectinload(models.Scan.results))
            result = await final_session.execute(stmt)
            scan = result.scalars().first()

            if scan:
                # Determine overall status: if any test errored -> ERROR, else COMPLETED
                final_scan_status = models.TestStatusEnum.COMPLETED
                all_tests_accounted_for = True
                if len(scan.results) != len(scan_result_ids):
                    all_tests_accounted_for = False
                    print(f"Warning: Mismatch in expected ({len(scan_result_ids)}) vs actual ({len(scan.results)}) results for scan {scan_id}.")

                for res in scan.results:
                    if res.status == models.TestStatusEnum.ERROR:
                        final_scan_status = models.TestStatusEnum.ERROR
                        break
                    elif res.status != models.TestStatusEnum.COMPLETED:
                        # Should not happen if gather() finished and individual tests handle errors, but as a safeguard
                        print(f"Warning: Test {res.id} for scan {scan_id} has status {res.status.value} after gather(). Marking scan as ERROR.")
                        final_scan_status = models.TestStatusEnum.ERROR
                        all_tests_accounted_for = False # Mark as incomplete if any test didn't finish properly
                        break

                if not all_tests_accounted_for:
                     final_scan_status = models.TestStatusEnum.ERROR # Ensure error if results are inconsistent

                scan.status = final_scan_status
                scan.completed_at = datetime.datetime.now(datetime.timezone.utc)
                print(f"All tests processed for Scan ID: {scan_id}. Final status: {final_scan_status.value}")
            else:
                print(f"Error: Scan with ID {scan_id} not found for final status update.")
            # Commit happens automatically


# --- API Endpoints ---

@app.get("/")
async def read_root():
    return {"message": "Penetration Testing API"}

@app.get("/tests", response_model=List[TestDefinitionResponse])
async def get_available_tests(db: AsyncSession = Depends(database.get_db)):
    """Returns a list of all available penetration tests."""
    stmt = select(models.TestDefinition).order_by(models.TestDefinition.id)
    result = await db.execute(stmt)
    test_defs = result.scalars().all()
    return test_defs


@app.post("/scans", response_model=ScanResponse, status_code=202) # 202 Accepted
async def start_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(database.get_db)
):
    """
    Accepts a URL and initiates a new penetration scan in the background.
    Returns the initial scan object with pending tests.
    """
    url_to_scan = str(scan_request.url) # Convert HttpUrl to string

    try:
        async with db.begin():
            # 1. Find or create the Website entry
            stmt_website = select(models.Website).filter_by(url=url_to_scan)
            result_website = await db.execute(stmt_website)
            website = result_website.scalars().first()

            if not website:
                website = models.Website(url=url_to_scan)
                db.add(website)
                await db.flush() # Get the ID for the new website
            elif website.last_scan_at:
                 # Optional: Check if a recent scan exists and maybe return that?
                 # Or just proceed with a new scan.
                 pass

            # 2. Get all available test definitions
            stmt_tests = select(models.TestDefinition)
            result_tests = await db.execute(stmt_tests)
            all_tests = result_tests.scalars().all()
            if not all_tests:
                 raise HTTPException(status_code=500, detail="No test definitions found in the database.")


            # 3. Create a new Scan entry
            new_scan = models.Scan(
                website_id=website.id,
                status=models.TestStatusEnum.PENDING
            )
            db.add(new_scan)
            await db.flush() # Get the ID for the new scan

            # 4. Create ScanResult entries for this scan
            for test_def in all_tests:
                scan_result = models.ScanResult(
                    scan_id=new_scan.id,
                    test_definition_id=test_def.id,
                    status=models.TestStatusEnum.PENDING,
                    result=models.TestResultEnum.NOT_RUN
                )
                db.add(scan_result)

            await db.flush() # Ensure all scan results have IDs if needed

            # Update website's last scan time
            website.last_scan_at = datetime.datetime.now(datetime.timezone.utc)

            # Fetch the newly created scan with relationships loaded for the response
            # Need to do this *before* commit to ensure the session contains the objects
            stmt_final_scan = select(models.Scan).where(models.Scan.id == new_scan.id).options(
                selectinload(models.Scan.website),
                selectinload(models.Scan.results).selectinload(models.ScanResult.test_definition)
            )
            result_final_scan = await db.execute(stmt_final_scan)
            final_scan_obj = result_final_scan.scalars().first()

            if not final_scan_obj:
                 # This indicates a problem retrieving the data just added within the transaction
                 raise HTTPException(status_code=500, detail="Failed to retrieve scan details after creation.")

            # Must convert to a dict *before* commit if using from_orm/from_attributes in response_model
            # because the session will be closed after commit.
            # Use .model_dump() for Pydantic v2
            response_data = ScanResponse.model_validate(final_scan_obj)


            # Add the background task *after* setting up the DB records
            background_tasks.add_task(run_all_tests_for_scan, new_scan.id, url_to_scan)

            # Commit happens automatically via 'async with db.begin()'

        # Return the data prepared before the commit
        return response_data

    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        # Log the exception details for debugging
        print(f"Error during scan initiation for {url_to_scan}: {e}")
        # Consider rolling back if necessary, though 'async with db.begin()' handles this
        raise HTTPException(status_code=500, detail=f"Internal server error during scan initiation: {e}")


@app.get("/scans/{scan_id}", response_model=ScanResponse)
async def get_scan_status(scan_id: int, db: AsyncSession = Depends(database.get_db)):
    """Returns the current status and results of a specific scan."""
    stmt = select(models.Scan).where(models.Scan.id == scan_id).options(
        selectinload(models.Scan.website),
        selectinload(models.Scan.results).selectinload(models.ScanResult.test_definition) # Load nested relations
    )
    result = await db.execute(stmt)
    scan = result.scalars().first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan with ID {scan_id} not found")
    return scan

# --- PDF Report Endpoint (Placeholder) ---

@app.get("/scans/{scan_id}/report")
async def download_scan_report(scan_id: int, db: AsyncSession = Depends(database.get_db)):
    """Generates and returns a PDF report for a completed scan."""
    # Fetch scan data (similar to get_scan_status)
    stmt = select(models.Scan).where(models.Scan.id == scan_id).options(
        selectinload(models.Scan.website),
        selectinload(models.Scan.results).selectinload(models.ScanResult.test_definition)
    )
    result = await db.execute(stmt)
    scan = result.scalars().first()

    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan with ID {scan_id} not found")

    # Allow report download even if scan ended in error, but not if pending/in_progress
    if scan.status not in [models.TestStatusEnum.COMPLETED, models.TestStatusEnum.ERROR]:
         raise HTTPException(status_code=400, detail=f"Scan {scan_id} is not yet complete. Status: {scan.status.value}")

    # --- Return simple message until PDF generation is implemented ---
    # Convert scan to dict for the JSON response (using Pydantic model)
    # Use .model_dump() for Pydantic v2
    scan_dict = ScanResponse.model_validate(scan).model_dump(mode='json') # Use mode='json' for datetime serialization
    return {"message": f"PDF report generation for scan {scan_id} is not yet implemented.", "scan_details": scan_dict}


# --- Uvicorn Runner (for local development) ---
if __name__ == "__main__":
    import uvicorn
    # Ensure PYTHONPATH includes the project root if running directly,
    # though running with 'uvicorn main:app' is generally preferred.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
