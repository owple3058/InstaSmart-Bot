import time
import random
import math
import sys
import os
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

# Ana dizinden config modülünü import edebilmek için
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class Humanizer:
    def __init__(self, driver):
        self.driver = driver

    def random_sleep(self, min_seconds=1.0, max_seconds=3.0):
        """Rastgele bekleme süresi."""
        if hasattr(config, "SAFE_MODE") and config.SAFE_MODE:
            min_seconds *= 1.5
            max_seconds *= 1.5
        time.sleep(random.uniform(min_seconds, max_seconds))

    def type_like_human(self, element, text):
        """Bir insann yazması gibi karakterler arası rastgele bekleyerek yazar."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))

    def smooth_scroll(self, pixels=None):
        """
        Sayfayı insan gibi yumuşakça kaydırır.
        pixels verilmezse rastgele bir miktar kaydırır.
        """
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        if pixels is None:
            # Rastgele 300-800px arası kaydır
            pixels = random.randint(300, 800)
            
        current_scroll = self.driver.execute_script("return window.pageYOffset")
        target_scroll = min(current_scroll + pixels, total_height - viewport_height)
        
        # Parça parça kaydır
        while current_scroll < target_scroll:
            step = random.randint(10, 50)
            current_scroll += step
            if current_scroll > target_scroll:
                current_scroll = target_scroll
                
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll});")
            time.sleep(random.uniform(0.01, 0.05))
            
        # Bazen hafif geri çıkıp tekrar in (doğallık için)
        if random.random() < 0.3:
            self.driver.execute_script(f"window.scrollBy(0, -{random.randint(20, 50)});")
            time.sleep(0.5)
            self.driver.execute_script(f"window.scrollBy(0, {random.randint(20, 50)});")

    def mouse_move_to_element(self, element):
        """Elementin üzerine doğru doğal bir eğri ile gitmeyi simüle eder (basitleştirilmiş)."""
        # Selenium ActionChains direkt gider, bunu biraz yumuşatmak zor ama offset ekleyebiliriz.
        action = ActionChains(self.driver)
        # Elementin ortası yerine rastgele bir noktasına git
        size = element.size
        w, h = size['width'], size['height']
        
        offset_x = random.randint(-int(w/4), int(w/4))
        offset_y = random.randint(-int(h/4), int(h/4))
        
        action.move_to_element_with_offset(element, offset_x, offset_y)
        action.pause(random.uniform(0.1, 0.5))
        return action

    def smart_click(self, element):
        """Elemente gider, biraz bekler ve tıklar."""
        try:
            action = self.mouse_move_to_element(element)
            action.click()
            action.perform()
        except:
            # Fallback
            self.driver.execute_script("arguments[0].click();", element)
