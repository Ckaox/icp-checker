#!/usr/bin/env python3
"""
Script para probar los roles de RR.HH. en la API de Render
Uso: python3 test_render.py
"""

import requests
import json

# URL de la API en Render
API_URL = "https://icp-checker.onrender.com/classify"

# Roles que deben clasificarse correctamente
test_roles = [
    'Chief People Officer',
    'CPO',
    'Administrativo de recursos humanos',
    'Desarrollo de RR. HH.',
    'Director de contratación',
    'Encargada de RR. HH.',
    'HR Generalist',
    'HRBP',
    'Generalista de RR. HH.',
    'técnico rrhh',
    'Chief People officer',
    'Talent acquisition',
    'HR technician',
    'Técnica de RRHH',
    'Human Resources Generalist',
    'Formador técnico',
    'Responsable de selección de personal',
    'Director de desarrollo',
    'R&D Director',
    'Human Resources Technician',
    'administrativo de RR. HH.',
    'Administrativa rrhh',
    'Administración de personal',
    'Director de contratación',
    'Talent Acquisition',
    'Chief People and Culture Officer',
    'Chief HR',
    'Directora de RRHH',
    'Directora de Recursos Humanos',
    'Puestos de recursos humanos',
]

# Roles que NO deben clasificarse (excluidos)
excluded_roles = [
    'Auxiliar de RR. HH.',
    'Becario de recursos humanos',
    'Human resources assistant',
]

def test_roles_api():
    print('=' * 100)
    print('PRUEBA DE ROLES DE RR.HH. EN RENDER')
    print('=' * 100)
    print(f'API URL: {API_URL}')
    print()
    
    # Test roles que deben clasificarse
    print('ROLES QUE DEBEN CLASIFICARSE:')
    print('-' * 100)
    print(f'{"Role":<50} {"Dept":<15} {"Generic Role":<30} {"Status"}')
    print('-' * 100)
    
    success_count = 0
    for role in test_roles:
        try:
            response = requests.post(
                API_URL,
                json={'roles': [role]},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    r = result[0]
                    dept = r.get('department', '')
                    role_generic = r.get('role_generic', '')
                    
                    if dept and dept != 'N/A':
                        status = '✅'
                        success_count += 1
                    else:
                        status = '❌ NO DETECTADO'
                    
                    print(f'{role:<50} {dept:<15} {role_generic:<30} {status}')
                else:
                    print(f'{role:<50} {"N/A":<15} {"N/A":<30} ❌ NO RESPONSE')
            else:
                print(f'{role:<50} {"ERROR":<15} {f"HTTP {response.status_code}":<30} ❌')
        except Exception as e:
            print(f'{role:<50} {"ERROR":<15} {str(e)[:30]:<30} ❌')
    
    print()
    print('ROLES QUE NO DEBEN CLASIFICARSE (EXCLUIDOS):')
    print('-' * 100)
    print(f'{"Role":<50} {"Dept":<15} {"Status"}')
    print('-' * 100)
    
    excluded_count = 0
    for role in excluded_roles:
        try:
            response = requests.post(
                API_URL,
                json={'roles': [role]},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    r = result[0]
                    dept = r.get('department', '')
                    
                    if not dept or dept == 'N/A':
                        status = '✅ Correctamente excluido'
                        excluded_count += 1
                    else:
                        status = f'❌ ERROR: Se clasificó como {dept}'
                    
                    print(f'{role:<50} {dept:<15} {status}')
                else:
                    print(f'{role:<50} {"N/A":<15} ✅ Correctamente excluido')
                    excluded_count += 1
            else:
                print(f'{role:<50} {"ERROR":<15} ❌ HTTP {response.status_code}')
        except Exception as e:
            print(f'{role:<50} {"ERROR":<15} ❌ {str(e)[:30]}')
    
    print()
    print('=' * 100)
    print(f'RESUMEN:')
    print(f'  Roles clasificados correctamente: {success_count}/{len(test_roles)} ({100*success_count//len(test_roles)}%)')
    print(f'  Roles excluidos correctamente: {excluded_count}/{len(excluded_roles)} ({100*excluded_count//len(excluded_roles) if len(excluded_roles) > 0 else 0}%)')
    print(f'  TOTAL: {success_count + excluded_count}/{len(test_roles) + len(excluded_roles)} ({100*(success_count + excluded_count)//(len(test_roles) + len(excluded_roles))}%)')
    print('=' * 100)

if __name__ == '__main__':
    test_roles_api()
