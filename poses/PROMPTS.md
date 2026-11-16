# Acti pose prompts

Used to generate new Acti poses for the sticker pack with an image AI tool (Canva AI, ChatGPT, Gemini). Attach the Acti model sheet as the reference image, then use **the base prompt plus one pose line**.

**Base prompt**
> The exact same 3D cartoon mascot character as the reference image (orange furry face and body, big brown eyes, blue-purple fur on the sides of the face, white and purple baseball cap with the heart logo, white zip hoodie, purple shorts, colourful sneakers), keeping the face, proportions, outfit and Pixar-style 3D rendering identical. New pose: **[POSE]**. Full body, plain pure white background, centered, soft studio lighting.

| # | Sticker | Pose | Status |
|---|---|---|---|
| 1 | LOL | laughing out loud, eyes squeezed shut with happy tears, mouth wide open, one hand holding its belly, the other slapping its knee, leaning back | ✅ |
| 2 | HMM… | thinking, one hand on its chin, eyes looking up to the side, one eyebrow raised, mouth pursed | ✅ |
| 3 | HI! / BYE BYE! | waving hello with one hand raised high, big open smile, head tilted, other hand on hip | ✅ |
| 4 | ON MY WAY! | running fast to the side, arms pumping, one leg up, determined happy face | ✅ |
| 5 | MABROOK! / YALLA! | jumping high celebrating, both arms raised, legs tucked, mouth open cheering | ✅ |
| 6 | LET'S GO! | big thumbs up toward the viewer and winking, cheeky grin | ✅ |
| 7 | LOVE IT! | heart shape with both hands in front of chest, sparkly eyes, blushing | ✅ |
| 8 | GOOD MORNING | big sleepy yawn, eyes half closed, both arms stretching above head | ✅ |
| 9 | SHUKRAN | palms pressed together, small polite bow, eyes closed in a warm smile | ✅ |
| 10 | OMG / WHAT?! | shocked, both hands on cheeks, huge eyes, mouth in an O | ✅ |
| 11 | GAME ON! | kicking a football mid-kick, arms out for balance, ball flying | ✅ |
| 12 | NOOO | dramatically crying in a cute funny way, streams of tears, fists rubbing eyes | ✅ |
| 13 | WHO'S IN? / HABIBI, COME! | pointing at the viewer, leaning forward, other hand beckoning | ✅ |
| 14 | ACTIVATED! | flexing both arms like a strongman, proud smile, chest puffed out | ✅ |
| 15 | WEEKEND! | dancing, one arm up, hips swinging, one foot lifted, eyes closed, big smile | ✅ |

Check every result against the model sheet before use. The AI sometimes simplifies the cap logo, so place the real logo back on the cap if needed.

Put the downloaded images (full size, any background) in `poses/`, named after the sticker, e.g. `poses/lol.png`. The sticker script cuts out the background itself.

## Acti Moves (no text)

Generated with Gemini 3 Pro Image (2K, square) using `poses/canva600/wave.png` as the reference, the base prompt above plus: *"No text, no brand logos on the sneakers or anywhere else."* When a result gave Acti a long striped tail, it was edited with this prompt (references: the result and `source/back.png`): *"Edit the first image: remove the long striped tail completely so the character has no long tail. This character only has a tiny round pompom tail on its lower back, as shown in the second image, which is hidden from this front angle. Keep everything else exactly identical."*

| File | Pose |
|---|---|
| skim_carry | standing proudly holding a colourful skimboard upright under one arm, the other hand giving a peace sign, big happy smile |
| skim_ride | riding a colourful skimboard sideways, gliding on a thin sheet of water with a splash spraying up behind the board, knees bent, arms out for balance, thrilled open-mouth smile |
| surf | riding a surfboard, crouched with arms out, a small curling blue wave splashing under the board, big excited smile |
| skateboard | doing an ollie on a colourful skateboard, both feet on the board in mid-air, arms out, thrilled grin |
| hiphop | hip-hop dancing, knees bent low, one arm crossed over the chest and the other pointing to the side, cool confident grin |
| disco | disco dancing, one finger pointing high to the sky, other hand on the hip, hips popped, eyes closed with a huge joyful smile |
| breakdance | breakdancing freeze, balancing on one hand with both legs kicked up in the air, playful excited face |
| party | happy party dancing with both arms up waving, one knee lifted high, mouth open laughing |
| volleyball | jumping high to spike a volleyball, one arm swinging at the ball above its head, determined happy face |
| padel | swinging a padel racket in a powerful forehand, a yellow ball flying off the racket, focused happy face |
| goalkeeper | goalkeeper diving sideways, gloved hands stretched out catching a football, determined face |
| yoga | yoga tree pose on one leg, palms pressed together, eyes closed, calm peaceful smile |
| weights | lifting a barbell with colourful plates high above the head, legs wide, straining but smiling |
| jumprope | skipping with a jump rope mid-hop, the rope looping over its head, cheerful face |
| trophy | holding a shiny golden trophy high, celebrating, mouth wide open cheering |
| medal | wearing a gold medal on a purple ribbon, playfully biting it, winking, thumbs up |
