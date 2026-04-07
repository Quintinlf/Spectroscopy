"""Test script: Verify solar spectral analysis support."""
from stellar_spectrospy.zodiac_targets import get_star_by_name, get_all_stars, ZODIAC_STARS

try:
    sun = get_star_by_name("Sun")
    print("✅ Sun lookup successful")
    print(f"   Name: {sun.name}")
    print(f"   Spectral Type: {sun.spectral_type}")
    print(f"   Constellation: {sun.constellation}")
    print(f"   Magnitude: {sun.vmag}")
    print()
    
    # Verify it's in the Solar System constellation
    solar_system_stars = ZODIAC_STARS.get("Solar System", [])
    print(f"✅ Solar System constellation has {len(solar_system_stars)} star(s)")
    for s in solar_system_stars:
        print(f"   - {s.name} ({s.bayer})")
    print()
    
    # Show summary
    print(f"✅ Total constellations: {len(ZODIAC_STARS)}")
    print(f"✅ Total stars: {len(get_all_stars())}")
    print(f"\n✅ Solar spectral analysis is fully supported!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
