# Chatbot SaaS

Welcome to Chatbot SaaS, a scalable and feature-rich platform for integrating AI-powered chatbots into your website.

## Features

- **AI-Powered Chatbot**: Leverage the capabilities of OpenAI's GPT-4 to provide intelligent responses.
- **Website Content Scraping**: Automatically scrape and index content from your website.
- **Document Support**: Upload documents as part of your knowledge base (Pro and Ultimate plans).
- **Voice Input**: Speech-to-text functionality for hands-free interaction (Ultimate plan).
- **Embeddable Widget**: Easily integrate the chatbot using a script tag.
- **Multi-tier Subscription Plans**: Choose from various plans tailored to different business needs.
- **Responsive Design**: Beautiful UI with modern design and responsiveness.
- **USD Pricing**: Simple, transparent pricing in US dollars.

## Setup and Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd chatbot_saas
   ```

2. **Setup Virtual Environment**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # On Windows using PowerShell
   
   # Activate for Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   
   Then do crawl4ai-setup
   
   ```

4. **Environment Variables**
   - Update the `.env` file with necessary keys:
     ```env
     SUPABASE_URL=https://your-supabase-instance.supabase.co
     SUPABASE_KEY=your-supabase-service-role-key
     OPENAI_API_KEY=your-openai-api-key
     SUPABASE_JWT_SECRET=your-jwt-secret
     SECRET_KEY=your-secret-key
     ```

5. **Run the Application**
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

6. **Visit the Application**
   Open your web browser and visit `http://localhost:8000`

## Subscription Plans

| Plan | Price (USD) | Features |
|------|-------------|----------|
| **Freemium** | Free | • 1 website<br>• 100 messages/month<br>• Basic features |
| **Starter** | $10/month | • 1 website<br>• Unlimited messages<br>• Text interaction only<br>• 30-day chat history |
| **Pro** | $20/month | • 1 website<br>• Up to 10 documents<br>• Document upload support<br>• White-label (no branding)<br>• 90-day chat history |
| **Ultimate** | $30/month | • Unlimited websites<br>• Up to 25 documents<br>• Voice input support<br>• White-label<br>• API access<br>• 365-day chat history |

### Voice Feature Browser Support
The voice input feature (Ultimate plan) is supported in:
- Chrome/Chromium (version 25+)
- Safari (version 14.1+)
- Edge (version 79+)
- Opera (version 27+)

Note: Firefox requires additional configuration for speech recognition.

## Database Setup

1. **Initial Setup**
   ```bash
   psql -U your_user -d your_database -f database_setup.sql
   ```

2. **Migration for Existing Data**
   If you have existing data, run the migration script:
   ```bash
   psql -U your_user -d your_database -f migrate_plans.sql
   ```

## License
This project is licensed under the MIT License.

## Contribution
Feel free to fork and contribute to this project by submitting a pull request.

