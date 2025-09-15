#!/usr/bin/env python3
from app import classify_one

# Lista de títulos a probar (del issue)
TITLES = [
    "Area Technical Manager",
    "Chief Information Technology Officer", 
    "Chief of Technology Transference & Venture Building",
    "Chief Product and Technology Officer",
    "Corporate Technical Director",
    "Corporate Technical Manager",
    "CTTO",
    "CQA",
    "Director del Área de Proyectos",
    "Director del área de tecnología", 
    "Director de tecnología",
    "Director Técnico",
    "Director Organización y Tecnología",
    "Engineering Manager",
    "Fullstack Technical Lead",
    "Head of Engineering",
    "Head of Project", 
    "IT Manager",
    "Jefe de Tecnología",
    "Lead Android Engineer",
    "Manager Technical Support",
    "Project Developer Manager", 
    "Project Technical Leader",
    "Quality Assurance & Technical Service Manager",
    "Responsable de tecnología de la información",
    "Senior Project Development Manager",
    "Tech Leader",
    "Technical Chief",
    "Technical Director", 
    "Technical lead",
    "Technical Manager",
    "VP of Engineering"
]

def test_all_roles():
    failed = []
    passed = []
    
    for title in TITLES:
        result = classify_one(title, [])
        
        if result["is_icp"] and result["role_generic"]:
            passed.append({
                "title": title,
                "department": result["department"], 
                "role": result["role_generic"],
                "why": result["why"]
            })
            print(f"✅ {title:<45} -> {result['role_generic']} ({result['department']})")
        else:
            failed.append({
                "title": title,
                "result": result
            })
            print(f"❌ {title:<45} -> NO DETECTADO ({result.get('why', {})})")
    
    print(f"\n🔸 RESUMEN: {len(passed)}/{len(TITLES)} roles detectados correctamente")
    print(f"🔸 FALLARON: {len(failed)} roles")
    
    if failed:
        print("\n--- ROLES QUE FALLARON ---")
        for item in failed:
            print(f"- {item['title']}: {item['result']}")
    
    return len(failed) == 0

if __name__ == "__main__":
    success = test_all_roles()
    exit(0 if success else 1)