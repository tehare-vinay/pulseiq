# Task 17 – Hosting Platform Comparison

| Criteria | Streamlit Community Cloud | Render Free | Hugging Face Spaces |
|---|---|---|---|
| Free limit | Free hosting | 750 instance hours/month | CPU Basic: 2 vCPU, 16 GB RAM |
| Data/storage | Approx. 50 GB maximum; resource limits apply | 512 MB RAM; no persistent disk on free web service | 50 GB non-persistent disk |
| Sleeping | 12 hours without traffic | 15 minutes without traffic | 48 hours without activity |
| Price | $0 | Free; paid compute from $7/month | CPU Basic free; upgrades paid |

## Selected Platform: Streamlit Community Cloud

Streamlit Community Cloud was selected because PulseIQ Analytics is
already built using Streamlit. It supports direct GitHub integration,
simplifies deployment of the existing multi-page dashboard, and offers
free hosting suitable for the initial project demonstration.

The application may sleep after 12 hours without traffic and can be
restarted by a visitor.

## Official References
- https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
- https://render.com/docs/free
- https://render.com/pricing
- https://huggingface.co/docs/hub/spaces-overview
- https://huggingface.co/docs/hub/spaces-gpus
- https://huggingface.co/pricing
