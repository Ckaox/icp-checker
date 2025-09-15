# ICP-Checker

## Descripción

ICP-Checker es una API REST desarrollada en FastAPI que clasifica automáticamente títulos de trabajo (job titles) para identificar si corresponden a un **Ideal Customer Profile (ICP)** en el contexto empresarial B2B.

El sistema analiza títulos de trabajo y determina:
- **Si es ICP**: Si el rol es relevante para ventas B2B
- **Departamento**: A qué área de la empresa pertenece
- **Subdivisión**: Especialización dentro del departamento
- **Nivel jerárquico**: Posición en la jerarquía organizacional
- **Rol genérico**: Categorización del puesto

## Instalación y Uso

### Instalación
```bash
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Endpoint Principal
```
POST /classify
```

## Formato de Input

```json
{
  "job_title": "Marketing Manager",
  "excludes": "intern,assistant,junior"
}
```

### Parámetros:
- **`job_title`** (requerido): Título del trabajo a clasificar
- **`excludes`** (opcional): Lista separada por comas de términos a excluir

## Formato de Output

```json
{
  "input": "Marketing Manager",
  "is_icp": true,
  "department": "Marketing",
  "subdivision": "General",
  "hierarchy_level": "Manager",
  "role_generic": "gerentes de marketing",
  "why": {
    "must": true,
    "seniority": true,
    "exclude": false,
    "matched": "area+seniority/special"
  }
}
```

### Campos de respuesta:
- **`input`**: Título original enviado
- **`is_icp`**: `true` si es ICP, `false` si no
- **`department`**: Departamento asignado
- **`subdivision`**: Subdivisión específica
- **`hierarchy_level`**: Nivel jerárquico detectado
- **`role_generic`**: Descripción genérica del rol
- **`why`**: Información de depuración sobre la clasificación

## Uso en Clay

### Configuración del HTTP API en Clay

1. **Crear nueva columna HTTP API**
2. **Configurar endpoint**:
   - **URL**: `https://tu-dominio.com/classify`
   - **Método**: `POST`
   - **Headers**: 
     ```
     Content-Type: application/json
     ```

3. **Configurar Body (JSON)**:
   ```json
   {
     "job_title": "{{job_title}}",
     "excludes": "intern,assistant,junior"
   }
   ```

4. **Mapear campos de respuesta**:
   - `is_icp` → Para filtrar leads válidos
   - `department` → Para segmentación por departamento
   - `hierarchy_level` → Para scoring por seniority
   - `subdivision` → Para personalización específica

### Ejemplo práctico en Clay

Si tienes una columna llamada `Job Title` con el valor "Marketing Manager":

**Request automático**:
```json
{
  "job_title": "Marketing Manager",
  "excludes": "intern,assistant,junior"
}
```

**Response**:
```json
{
  "input": "Marketing Manager",
  "is_icp": true,
  "department": "Marketing",
  "subdivision": "General",
  "hierarchy_level": "Manager",
  "role_generic": "gerentes de marketing"
}
```

### Casos de uso en Clay

- **Filtrado de leads**: Usar `is_icp` para filtrar solo contactos relevantes
- **Segmentación**: Agrupar por `department` para campañas específicas
- **Scoring**: Asignar puntuación según `hierarchy_level`
- **Personalización**: Adaptar mensajes según `subdivision`

## Departamentos Soportados

### 1. **Tecnología**
- **Subdivisiones**: Data, Engineering, Technical, Product, Infrastructure, DevOps, QA, Security
- **Ejemplos**: Software Engineer, Data Scientist, DevOps Engineer, IT Manager

### 2. **Marketing**
- **Subdivisiones**: Digital, Traditional, Content, Growth, Performance, Social
- **Ejemplos**: Marketing Manager, Brand Manager, Content Manager, Growth Manager

### 3. **Ventas**
- **Subdivisiones**: Inside Sales, Field Sales, Channel, Key Accounts
- **Ejemplos**: Sales Manager, Account Manager, Business Development Manager

### 4. **Finanzas**
- **Subdivisiones**: General, Accounting, Treasury, Control, FP&A, Credit
- **Ejemplos**: Financial Analyst, Controller, Treasury Manager, CFO

### 5. **Operaciones**
- **Subdivisiones**: General, Logistics, Supply Chain, Quality, Customer Service
- **Ejemplos**: Operations Manager, Supply Chain Manager, Logistics Manager

### 6. **RR. HH.**
- **Subdivisiones**: Talent, Compensation, Learning, Business Partner
- **Ejemplos**: HR Manager, Recruiter, Compensation Manager, Training Manager

### 7. **Ejecutivo**
- **Subdivisiones**: General, Strategy, Operations, Commercial
- **Ejemplos**: CEO, General Manager, Vice President, Managing Director

### 8. **Legal**
- **Subdivisiones**: General, Corporate, Compliance, Contracts, Privacy
- **Ejemplos**: Legal Manager, General Counsel, Compliance Manager

### 9. **Producto**
- **Subdivisiones**: Management, Design, Strategy, Research
- **Ejemplos**: Product Manager, Product Director, UX Designer, Product Owner

## Niveles Jerárquicos

### **C-Suite**
- CEO, CFO, CTO, CMO, CIO, COO, etc.

### **VP/Director**
- Vice President, Director, Director General, Managing Director

### **Manager**
- Manager, Gerente, Jefe, Head, Lead

### **Lead**
- Team Lead, Principal, Senior Lead, Coordinator

### **Specialist**
- Specialist, Engineer, Analyst, Scientist, Consultant, Representative

## Ejemplos de Uso

### Ejemplo 1: Marketing Manager
```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{"job_title": "Marketing Manager"}'
```

**Respuesta:**
```json
{
  "input": "Marketing Manager",
  "is_icp": true,
  "department": "Marketing",
  "subdivision": "General",
  "hierarchy_level": "Manager",
  "role_generic": "gerentes de marketing"
}
```

### Ejemplo 2: Junior Developer (excluido)
```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{"job_title": "Junior Software Developer"}'
```

**Respuesta:**
```json
{
  "input": "Junior Software Developer",
  "is_icp": false,
  "department": "",
  "subdivision": "",
  "hierarchy_level": "",
  "role_generic": "",
  "why": {"excluded_by": "junior pattern"}
}
```

### Ejemplo 3: CEO
```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{"job_title": "Chief Executive Officer"}'
```

**Respuesta:**
```json
{
  "input": "Chief Executive Officer",
  "is_icp": true,
  "department": "Ejecutivo",
  "subdivision": "General",
  "hierarchy_level": "C-Suite",
  "role_generic": "CEOs"
}
```

## Configuración

### Exclusiones Automáticas
El sistema excluye automáticamente roles con:
- `junior`, `jr`, `trainee`, `becario`, `intern`
- `assistant`, `asistente`
- `community`, `artist`, `art`
- `design`, `diseño`, `advisor`
- `paid`, `customer`

### Exclusiones Personalizadas
Usa el parámetro `excludes` para agregar términos específicos:
```json
{
  "job_title": "Senior Marketing Manager",
  "excludes": "senior,lead"
}
```

## Health Check

```bash
curl -X GET "http://localhost:8000/health"
```