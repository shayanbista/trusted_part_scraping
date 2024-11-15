def extract_button_info(button):
    divs = button.find_all("div")
    risk_content = (
        divs[0].get_text(strip=True) if len(divs) > 0 else "Content not found"
    )
    risk_level = divs[1].get_text(strip=True) if len(divs) > 1 else "Level not found"
    return risk_content, risk_level
