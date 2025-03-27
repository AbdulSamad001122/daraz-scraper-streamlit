import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
from sqlalchemy.orm import Session
from models import Product, SessionLocal
import asyncio
import sys
import os
os.system("playwright install")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def save_products_to_db(products):
    db: Session = SessionLocal()
    try:
        for product in products:
            db_product = Product(
                title=product["title"],
                price=product["price"],
                link=product["link"]
            )
            db.add(db_product)
        db.commit()
        st.success(f"Saved {len(products)} products to the database.")
    finally:
        db.close()

def save_products_to_csv(products, file_name="products.csv"):
    # Convert the products list to a DataFrame
    df = pd.DataFrame(products)
    
    # If the file already exists, append new data
    try:
        existing_df = pd.read_csv(file_name)
        df = pd.concat([existing_df, df], ignore_index=True)
    except FileNotFoundError:
        pass

    # Remove duplicates where title, price, and link are identical
    df = df.drop_duplicates(subset=["title", "price", "link"], keep="first")

    # Save the updated DataFrame back to the CSV file
    df.to_csv(file_name, index=False)

    st.success("Products saved to CSV file without duplicates!")

def scrape_daraz(query, start_page, end_page):
    products = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for i in range(start_page, end_page + 1):
            url = f"https://www.daraz.pk/catalog/?page={i}&q={query}"
            page.goto(url)
            page.wait_for_timeout(3000)
            products_cards = page.locator(".qmXQo").all()
            for product in products_cards:
                title = product.locator(".RfADt a").text_content()
                price = product.locator(".ooOxS").text_content()
                link = product.locator(".RfADt a").get_attribute("href")
                link = "https:" + link if link.startswith("//") else link
                products.append({"title": title.strip(), "price": price.strip(), "link": link})
        browser.close()
    return products

st.title("Daraz Product Scraper")
query = st.text_input("Product Name:", "")
start_page = st.number_input("Start Page:", min_value=0, value=0)
end_page = st.number_input("End Page:", min_value=1, value=1)

if st.button("Search"):
    if query:
        with st.spinner("Scraping products..."):
            products = scrape_daraz(query, start_page, end_page)
            if products:
                save_products_to_db(products)
                save_products_to_csv(products)
                df = pd.DataFrame(products)
                st.write(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "products.csv", "text/csv")
            else:
                st.warning("No products found.")
    else:
        st.error("Please enter a product name.")