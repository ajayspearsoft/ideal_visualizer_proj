from typing import Dict, List


ROOM_PROMPTS: Dict[str, List[str]] = {
    "bedroom": [
        (
    "Photorealistic interior photography, Indian master bedroom, DSLR shot, natural daylight. King bed dark grey tufted upholstered headboard, vertical charcoal louvers slatted wood panels on the bed back wall, brown cushions, linen bedsheet, foreground lower frame. Full-wall closed modular wardrobe mint sage laminate shutters black slim handles bottom drawers. Illuminated mirror niche warm LED strip. Wall-mounted TV unit sage green. POP false ceiling cove lighting strips ceiling fan recessed spotlights. Large format white marble vitrified tile floor. Sheer curtains window. Beige cream walls. Premium Indian apartment, realistic textures, no CGI, no animation, photographic quality, 8k."
),
(
    "Real photo Indian master bedroom, not render not illustration. King bed tufted fabric headboard grey, bed background wall with premium vertical wood louvers and slatted paneling, side tables, close to camera foreground. One full wall closed laminate wardrobe mint green shutters long black handles storage drawers. Dressing mirror niche LED backlit. TV panel wall mounted. POP ceiling fan warm cove light recessed spots. White marble floor tiles. Cream beige walls curtains window. Middle class premium Indian apartment interior, believable materials textures lighting, photorealistic 8k DSLR."
),
(
    "Modern Indian apartment bedroom real photograph. Complete king bed upholstered headboard fabric grey, textured bed back wall with decorative louvers and warm LED strips, linen sheets cushions foreground. Closed full wall modular wardrobe sage mint laminate shutters handles drawers. Mirror niche warm glow TV unit. False POP ceiling indirect cove light ceiling fan spotlights. Vitrified marble look floor tiles. Soft beige ivory walls sheer curtains. Balanced practical layout warm ambient light realistic laminate fabric materials subtle decor, not CGI not animated not showroom, photographic quality 8k."
),
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
    "Photorealistic interior photography, modern Indian modular kitchen, DSLR. Solid modular base and wall cabinets charcoal grey, seamless black granite countertop, stainless steel sink and tap. Tiled backsplash, built-in oven and hob. POP false ceiling recessed spots. Large format floor tiles. Natural window light. Clean clutter-free layout, realistic materials, no CGI 8k."
),
(
    "Real photo Indian kitchen, modular cabinets light wood finish, white marble countertop, built-in chimney. Strictly solid modular cabinetry, replace all open shelving with closed laminate shutters. Backlit backsplash, ceiling spotlights. Realistic textures, photographic quality, not a render 8k."
),
(
    "Modern Indian kitchen real photograph. Solid base cabinets wood tone matte laminate. White matte overhead cabinets long vertical handles. Granite or composite countertop black grey. False ceiling with downlights. Beige white tile walls. Grey vitrified floor. Clean functional layout, realistic proportions, warm task lighting, photographic quality 8k."
),
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
    "Real photo Indian kitchen, DSLR shot, bright natural daylight. L-shaped modular kitchen layout. Base cabinets dark wood laminate grey matte shutters. Overhead white matte laminate cabinets vertical handles. Countertop black granite. Stainless steel sink faucet. Chimney over hob hob not fully visible. Under cabinet LED strips. Storage drawers cabinets. Small appliances mixer grinder toaster microwave on counter. Grey vitrified tile floor. White beige walls. Clean organized practical Indian kitchen, realistic textures, not CGI, photographic quality 8k."
),
    "bathroom": (
    "Real photo Indian bathroom, bright natural daylight. White vanity with countertop sink faucet mirror above. Wall mounted mirror with warm LED strip light. Glass shower cubicle with frosted glass panel showerhead. Wall tiles white marble look matte finish. Floor tiles darker grey matte anti-skid. Ceiling with false POP white cove lights downlights exhaust fan. Sanitary fittings white ceramic WC bidet. Towel rail accessories. Small bathroom, practical layout, premium Indian apartment style, realistic textures, not CGI, photographic quality 8k."
),

        
}


def get_default_room_prompt(room_type: str) -> str:
    prompts = ROOM_PROMPTS.get(room_type, ROOM_PROMPTS["bedroom"])
    return prompts[0].strip()
