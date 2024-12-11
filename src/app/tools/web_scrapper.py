import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import chainlit as cl
import io

async def scrape_even_titles_to_pdf(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all even title hierarchy (h2, h4, h6)
        titles = soup.find_all(['h2', 'h4', 'h6'])
        
        # Create a PDF document in memory
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        total_size = 0  # Initialize total size in bytes
        
        # Add each even title to the PDF
        for title in titles:
            if int(title.name[1]) % 2 == 0:  # Check if the title level is even
                title_text = title.get_text()
                pdf.multi_cell(0, 10, title_text, 0, 1)
                
                # Add the content following the title
                content = title.find_next_sibling()
                while content and content.name not in ['h2', 'h4', 'h6']:
                    if content.name == 'p':  # Only include paragraphs
                        paragraph_text = content.get_text()
                        pdf.multi_cell(0, 10, paragraph_text)
                        total_size += len(paragraph_text.encode('utf-8'))  # Update total size

                    # Check if the PDF size exceeds 50 MB
                    if total_size > 50 * 1024 * 1024:  # 50 MB in bytes
                        cl.message("The generated PDF has exceeded 50 MB and will be truncated.")
                        pdf.output(io.BytesIO())  # Save the current state
                        return
                    
                    content = content.find_next_sibling()
        
        # Save the PDF to a bytes buffer
        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        # Send the PDF file as an attachment in a Chainlit message
        cl.message("Here is the PDF file with the scraped content.", attach=pdf_output)
    else:
        cl.message("Failed to retrieve content: {response.status_code}")