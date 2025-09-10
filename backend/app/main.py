from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.routes.auth import router as auth_router
from backend.app.routes.chat import router as chat_router
from backend.app.routes.embed import router as embed_router
from backend.app.routes.knowledgebase import router as kb_router
from backend.app.routes.dashboard import router as dashboard_router
from backend.app.routes.plans import router as plans_router
from backend.app.routes.payments import router as payment_router
from backend.app.routes.pricing import router as pricing_router

app = FastAPI(title="Chatbot SaaS")

# Serve static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(embed_router)
app.include_router(kb_router)
app.include_router(dashboard_router)
app.include_router(plans_router)
app.include_router(payment_router)
app.include_router(pricing_router)

# Test scraper router
from backend.app.routes.test_scraper import router as test_scraper_router
app.include_router(test_scraper_router)

@app.get("/", response_class=HTMLResponse)
def serve_index():
    with open("frontend/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard.html", response_class=HTMLResponse)
def serve_dashboard_html():
    with open("frontend/dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    """Serve dashboard page (for Stripe redirect)"""
    with open("frontend/dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/plans", response_class=HTMLResponse) 
def serve_plans():
    """Serve plans page (for Stripe cancel redirect)"""
    # For now, redirect to index since we don't have a separate plans page
    with open("frontend/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/payment-success", response_class=HTMLResponse)
def serve_payment_success():
    """Serve payment success page"""
    # Create a simple success page that redirects to login
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful</title>
        <style>
            body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
            .container { text-align: center; padding: 2rem; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .success-icon { color: #4CAF50; font-size: 48px; margin-bottom: 1rem; }
            h1 { color: #333; }
            p { color: #666; margin: 1rem 0; }
            .btn { display: inline-block; padding: 12px 30px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin-top: 1rem; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✓</div>
            <h1>Payment Successful!</h1>
            <p>Your subscription has been activated successfully.</p>
            <p>Please log in to access your dashboard and start using your plan.</p>
            <a href="/" class="btn">Go to Login</a>
        </div>
        <script>
            // Auto redirect to login after 5 seconds
            setTimeout(() => {
                window.location.href = '/?payment=success';
            }, 5000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# Run app with following
# uvicorn backend.app.main:app --reload --port 8000
# or uvicorn app.main:app --reload
