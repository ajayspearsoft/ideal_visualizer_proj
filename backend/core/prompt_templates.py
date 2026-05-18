from typing import Dict, List


ROOM_PROMPTS: Dict[str, List[str]] = {
    "bedroom": [
        (
            "Ultra-realistic modern Indian bedroom interior renovation. Preserve exact same room geometry, walls, window, and floor tiles exactly. Add a king size bed with a clean modern white bedsheet. Convert any existing built-in open shelves or alcoves into premium modular wardrobes in a clean matte laminate finish with elegant vertical bronze handles, built flush into the wall cavities. Add a floating TV console unit. Add a sleek dark ceiling fan to the ceiling. Glossy white floor tiles remain exactly unchanged. DSLR architectural photography, photorealistic textures, vibrant bright lighting, highly detailed 8k."
        ),
        (
            "Photorealistic Indian bedroom design. Preserve original room shape, exact wall positions, windows, and structural dimensions perfectly. Edit only by adding modular wardrobe systems with closed flat shutters and premium laminate finish over the shelf cavities. Place a premium bed with modern bedding aligned within the room layout on the floor footprint. Include a modern dark ceiling fan on the ceiling. Room size and perspective must remain completely unaltered. Highly realistic shadows, perfect perspective matching, DSLR quality, 8k resolution."
        )
    ],
    "living_room": [
        (
    "Photorealistic Indian living room, DSLR shot, natural daylight. L-shaped sofa grey upholstery cushions foreground. TV wall with mounted TV slim entertainment unit closed cabinets white matte finish wooden laminate. False POP ceiling dual tone white beige cove lights recessed spotlights ceiling fan. Large vitrified tiles white marble look floor. Sheer curtains large window. Light beige walls. Premium Indian apartment interior, realistic textures, not CGI, photographic quality 8k."
),
(
    "Real photo living room apartment India. Full size sofa grey fabric cushions pillows, coffee table. One TV unit wall mounted TV wooden cabinets drawers. POP ceiling white warm indirect lighting cove strips ceiling fan recessed spotlights. Light vitrified floor tiles grey beige tone. Sheer curtains window. Soft neutral walls. Realistic proportions materials, middle class to premium style, preserve room geometry, photorealistic 8k DSLR."
),
(
    "Modern Indian living hall real photograph. Realistic L-shaped sofa grey fabric close to camera. Wall mounted TV entertainment unit white wood matte laminate. False POP ceiling with LED cove lighting recessed downlights ceiling fan. Large white grey vitrified tiles floor. Pastel walls sheer curtains window. Clean practical layout not cluttered, warm ambient lighting, realistic materials, photographic quality 8k."
),
        
    ],
    "kitchen": [
        (
            "Ultra-realistic modular kitchen renovation edit. Preserve the exact same room structure, shelf dimensions, ceiling, walls, floor tiles, and camera angle. Convert open white shelves into simple Indian-style modular shutters by adding thin pastel light green matte laminate panel doors over the shelves, keeping original divisions. Add a black ceiling fan at the top, and a realistic modern stainless steel refrigerator fitted neatly into the right-side empty wall area near the switchboard. On the black stone countertop, place a modern Indian gas stove/hob. The top horizontal open loft storage remains divided into 2-3 open compartments. Keep some shelves partially visible for a realistic display look. Add subtle warm LED lighting inside a few open shelf sections. DSLR real-estate photography style, soft realistic shadows, highly detailed matte textures, 8k resolution, authentic Indian modular kitchen."
        ),
        (
            "Ultra-realistic Indian modular kitchen design edit. Convert existing white shelves to modular cabinetry with soft mint green and matte light green laminate panel doors. Keep original shelf divisions, camera angle, and walls identical. Mount a sleek black ceiling fan to the top ceiling. Fit a double-door modern metallic refrigerator perfectly into the right wall recess. Place an Indian multi-burner gas stove on the black stone counter. Leave some middle shelves open for display, illuminated by warm subtle interior LED lights. Top horizontal storage sections remain open compartments. Photo-realistic renovation, DSLR architectural photography, soft natural lighting and realistic depth, 8k."
        )
    ],
    "bathroom": [
        (
    "Photorealistic Indian bathroom, DSLR shot, natural daylight. White vanity with countertop sink faucet mirror above. Wall mounted mirror with warm LED strip light. Glass shower cubicle with frosted glass panel showerhead. Wall tiles white marble look matte finish. Floor tiles darker grey matte anti-skid. Ceiling with false POP white cove lights downlights exhaust fan. Sanitary fittings white ceramic WC bidet. Towel rail accessories. Small bathroom, practical layout, premium Indian apartment style, realistic textures, not CGI, photographic quality 8k."
),
(
    "Real photo modern bathroom India. White vanity cabinet countertop sink. Mirror wall mounted backlit. Glass shower cubicle shower panel. Large format white beige wall tiles matte. Anti-skid grey floor tiles. White ceiling recessed downlights LED strips exhaust fan. White ceramic fittings WC bidet. Premium middle class apartment bathroom, realistic materials, photographic quality 8k."
),
(
    "Modern Indian bathroom real photograph. White vanity wooden cabinet under-sink storage. Large rectangular mirror warm LED strip light. Glass shower partition shower panel. Wall tiles white marble finish matte. Grey textured floor tiles anti-skid. False POP ceiling with warm cove lighting recessed lights ceiling fan. White WC bidet shower fittings. Towel rack mirror soap holder. Compact efficient layout, premium look, photographic quality 8k."
),

        
    ],
}


ROOM_PRESETS: Dict[str, str] = {
    "living_room": (
    "Real photo Indian living room, L-shaped sofa grey upholstery cushions pillows coffee table, TV unit mounted TV wooden cabinets drawers, POP ceiling white warm indirect lighting cove strips ceiling fan recessed spotlights, light vitrified floor tiles grey beige tone, sheer curtains window soft neutral walls realistic proportions materials middle class to premium style preserve room geometry photorealistic 8k DSLR."
),
    "bedroom": (
    "Real photo Indian bedroom, large bed with upholstered headboard grey fabric cushions pillows. Full wall modular wardrobe closed shutters dark wood matte finish vertical handles. TV unit niche with mounted TV white laminate base cabinet. False POP ceiling white beige dual tone with warm LED cove lighting ceiling fan recessed spotlights. Light grey beige vitrified floor tiles marble look. Pastel walls sheer curtains window. Premium middle class Indian bedroom, realistic laminate and fabric materials, not animated not CGI not closet display, preserve room geometry, photorealistic 8k DSLR."
),
    "kitchen": (
        "Real photo Indian modular kitchen, DSLR shot, bright natural daylight. Convert existing open white shelves to simple Indian-style modular shutters with thin light green matte laminate panel doors. Keep original divisions. Add a sleek black ceiling fan to the top ceiling. Fit a modern stainless steel refrigerator perfectly into the right wall area near the switchboard. Place a realistic Indian gas stove on the black stone countertop. The top horizontal open loft storage remains divided into 2-3 open compartments, and some shelves are left partially open showing items with subtle warm interior LED lighting. Clean organized Indian modular kitchen, realistic matte textures, no CGI, photorealistic 8k DSLR."
    ),
    "bathroom": (
    "Real photo Indian bathroom, bright natural daylight. White vanity with countertop sink faucet mirror above. Wall mounted mirror with warm LED strip light. Glass shower cubicle with frosted glass panel showerhead. Wall tiles white marble look matte finish. Floor tiles darker grey matte anti-skid. Ceiling with false POP white cove lights downlights exhaust fan. Sanitary fittings white ceramic WC bidet. Towel rail accessories. Small bathroom, practical layout, premium Indian apartment style, realistic textures, not CGI, photographic quality 8k."
),

        
}


def get_default_room_prompt(room_type: str) -> str:
    prompts = ROOM_PROMPTS.get(room_type, ROOM_PROMPTS["bedroom"])
    return prompts[0].strip()
