from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os
import io
from io import BytesIO

class PosterGenerator:
    def __init__(self, output_dir="output"):
        self.width = 1080
        self.height = 1350
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Fonts (Bahnschrift is ideal for this German car look)
        self.font_main = "bahnschrift.ttf"
        self.font_fallback = "arial.ttf"

    def _get_font(self, size, bold=False, condensed=False):
        """Helper to safely load bahnschrift or arial."""
        try:
            return ImageFont.truetype(self.font_main, size)
        except:
            try:
                fname = "arialbd.ttf" if bold else "arial.ttf"
                return ImageFont.truetype(fname, size)
            except:
                return ImageFont.load_default()

    def create_poster(self, car_data):
        # 1. Create Canvas (Clean White)
        bg_color = (255, 255, 255)
        img = Image.new('RGB', (self.width, self.height), color=bg_color)
        draw = ImageDraw.Draw(img)

        margin = 100

        # 2. Draw Grey Block
        block_color = (242, 242, 242) # Very light grey
        block_width = int(self.width * 0.75)
        block_height = 700
        block_x = (self.width - block_width) // 2
        block_y = 350
        draw.rectangle([block_x, block_y, block_x + block_width, block_y + block_height], fill=block_color)

        # 3. Typography (Top Left)
        make_text = car_data['make'].upper()
        model_text = car_data['model'].upper()

        # Strip redundant make from model (e.g. "AUDI Q2" -> "Q2")
        if model_text.startswith(make_text):
            model_text = model_text[len(make_text):].strip()

        # Dynamic Scaling for Make Name
        title_size = 180
        while title_size > 60:
            title_font = self._get_font(title_size, bold=True)
            bbox = draw.textbbox((margin, margin), make_text, font=title_font, stroke_width=2)
            if (bbox[2] - bbox[0]) <= (self.width - 2 * margin):
                break
            title_size -= 10

        make_color = (130, 130, 135) # Slightly darker grey for better visibility
        model_color = (0, 0, 0)       # Black for model

        # stroke_width makes it bolder
        draw.text((margin, margin), make_text, font=title_font, fill=make_color, stroke_width=3)

        # Dynamic Scaling for Model Name
        subtitle_size = 110
        while subtitle_size > 40:
            subtitle_font = self._get_font(subtitle_size, bold=True)
            # Offset vertical position based on title_size
            y_offset = margin + int(title_size * 0.95)
            bbox = draw.textbbox((margin, y_offset), model_text, font=subtitle_font)
            if (bbox[2] - bbox[0]) <= (self.width - 2 * margin):
                break
            subtitle_size -= 5

        draw.text((margin, y_offset), model_text, font=subtitle_font, fill=model_color)

        # 4. Car Image (Centered with Shadow and BG removal)
        image_path = car_data.get('image_path')
        if image_path and os.path.exists(image_path):
            try:
                from rembg import remove
                with open(image_path, 'rb') as i:
                    input_data = i.read()
                    output_data = remove(input_data)

                car_img = Image.open(io.BytesIO(output_data)).convert("RGBA")

                # --- NEW: Autocrop to remove transparent margins ---
                bbox = car_img.getbbox()
                if bbox:
                    car_img = car_img.crop(bbox)
                # --------------------------------------------------

                # Resize
                target_width = int(self.width * 0.90)
                ratio = target_width / car_img.width
                target_height = int(car_img.height * ratio)
                car_img = car_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

                # Position
                y_pos = block_y + (block_height // 2) - (target_height // 2) + 100

                # --- NEW: Dual-Layer Shadow (Reference Style) ---
                # 1. Ambient Shadow (Soft and widespread)
                ambient_h = 100
                ambient_shadow = Image.new('RGBA', (target_width, ambient_h), (0, 0, 0, 0))
                a_draw = ImageDraw.Draw(ambient_shadow)
                a_draw.ellipse([20, 20, target_width - 20, ambient_h - 10], fill=(0, 0, 0, 35))
                ambient_shadow = ambient_shadow.filter(ImageFilter.GaussianBlur(35))
                img.paste(ambient_shadow, ((self.width - target_width) // 2, y_pos + target_height - 60), ambient_shadow)

                # 2. Contact Shadow (Darker and sharper under tires)
                contact_h = 40
                contact_shadow = Image.new('RGBA', (target_width, contact_h), (0, 0, 0, 0))
                c_draw = ImageDraw.Draw(contact_shadow)
                c_draw.ellipse([40, 10, target_width - 40, contact_h - 5], fill=(0, 0, 0, 90))
                contact_shadow = contact_shadow.filter(ImageFilter.GaussianBlur(6))
                img.paste(contact_shadow, ((self.width - target_width) // 2, y_pos + target_height - 35), contact_shadow)
                # -----------------------------------------------

                img.paste(car_img, ((self.width - target_width) // 2, y_pos), car_img)

            except Exception as e:
                print(f"Error processing image: {e}")
                car_img = Image.open(image_path).convert("RGBA")

                # Autocrop fallback
                bbox = car_img.getbbox()
                if bbox:
                    car_img = car_img.crop(bbox)

                target_width = self.width - (margin * 2)
                ratio = target_width / car_img.width
                target_height = int(car_img.height * ratio)
                car_img = car_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                img.paste(car_img, (margin, 500), car_img)

        # 5. Footer (YEAR left, Specs Grid right)
        footer_y = 1120
        label_font = self._get_font(24, bold=True)
        # Spec values same size as labels, but regular weight
        spec_value_font = self._get_font(24)

        label_color_dark = (40, 40, 45)
        value_color_black = (0, 0, 0)
        grey_text_color = (120, 120, 125)

        # 5.1 YEAR Block
        # Refined: Large bold label, small bold value closer together
        year_label_font = self._get_font(44, bold=True)
        year_value_font = self._get_font(22, bold=True)

        draw.text((margin, footer_y), "YEAR", font=year_label_font, fill=value_color_black, stroke_width=1)
        # Vertical gap reduced (footer_y + 48)
        draw.text((margin, footer_y + 48), str(car_data.get('year', 'N/A')), font=year_value_font, fill=grey_text_color)

        # Divider Line (Vertical)
        line_x = margin + 200
        draw.line([line_x, footer_y, line_x, footer_y + 180], fill=(200, 200, 205), width=2)

        # 5.2 Specs Columns
        raw_specs = car_data.get('specs', {})
        specs = {k.lower(): v for k, v in raw_specs.items()}

        # --- DATA FORMATTING & CONVERSION ---
        import re
        # 1. Engine cm3 -> L
        engine_val = specs.get("engine", "N/A")
        if "cm3" in str(engine_val):
            try:
                digits = re.search(r'(\d+)', str(engine_val)).group(1)
                liters = round(float(digits) / 1000, 1)
                formatted_engine = f"{liters} L"
            except: formatted_engine = engine_val
        else: formatted_engine = engine_val

        # 2. Acceleration -> s
        accel_val = specs.get("0-100", "N/A")
        if accel_val != "N/A" and "s" not in str(accel_val):
            formatted_accel = f"{accel_val} s"
        else: formatted_accel = accel_val

        # 3. Torque (Prefer Nm)
        torque_val = specs.get("torque", "N/A")

        # 4. Top Speed -> km/h
        top_val = specs.get("top_speed", "N/A")
        if top_val != "N/A" and "km/h" not in str(top_val):
            formatted_top = f"{top_val} km/h"
        else: formatted_top = top_val
        # ------------------------------------

        col1_x = line_x + 50
        col2_x = col1_x + 360 # Increased spacing
        row_h = 50

        col1_items = [
            ("Engine", formatted_engine),
            ("Power", specs.get("power")),
            ("Torque", torque_val),
            ("Weight", specs.get("weight"))
        ]

        col2_items = [
            ("0-100 km/h", formatted_accel),
            ("Top speed", formatted_top)
        ]

        def draw_spec(x, y, label, val):
            # Bold labels using stroke_width=1
            draw.text((x, y), label, font=label_font, fill=label_color_dark, stroke_width=1)

            # Dynamic proximity: Get label width to place value precisely
            bbox = draw.textbbox((x, y), label, font=label_font, stroke_width=1)
            label_w = bbox[2] - bbox[0]

            display_val = str(val) if (val and val != "N/A" and val != "-") else "N/A"
            # Place value with a small consistent gap (15px)
            draw.text((x + label_w + 15, y), display_val, font=spec_value_font, fill=value_color_black)

        for i, (lbl, val) in enumerate(col1_items):
            draw_spec(col1_x, footer_y + i * row_h, lbl, val)

        for i, (lbl, val) in enumerate(col2_items):
            draw_spec(col2_x, footer_y + i * row_h, lbl, val)

        # 5.3 Flag (Bottom Right)
        country_code = car_data.get('country_code', 'de').lower()
        flag_path = f"assets/flags/{country_code}.png"
        if os.path.exists(flag_path):
            try:
                flag_img = Image.open(flag_path).convert("RGBA")
                flag_img = flag_img.resize((90, 60), Image.Resampling.LANCZOS)
                img.paste(flag_img, (self.width - margin - 90, footer_y + 115), flag_img)
            except: pass

        # 6. Save
        output_filename = f"{car_data['make']}_{car_data['model']}.png".replace(" ", "_").replace("/", "_").lower()
        output_path = os.path.join(self.output_dir, output_filename)
        img.save(output_path)
        print(f"Assignment-style poster saved to {output_path}")
        return output_path

if __name__ == "__main__":
    from mock_data import MOCK_CAR_DATA
    gen = PosterGenerator()
    gen.create_poster(MOCK_CAR_DATA)
