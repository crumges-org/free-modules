# Módulo de Automatización WooCommerce - Guía de Usuario

**Versión:** 18.0.1.0.0  
**Desarrollado por:** ECOSIRE (PRIVATE) LIMITED  
**Sitio Web:** https://www.ecosire.com/  
**Soporte:** info@ecosire.com

---

## Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Instalación y Configuración](#instalación-y-configuración)
3. [Primeros Pasos](#primeros-pasos)
4. [Configuración](#configuración)
5. [Panel de Control](#panel-de-control)
6. [Sincronización](#sincronización)
7. [Herramientas y Asistentes](#herramientas-y-asistentes)
8. [Informes y Monitoreo](#informes-y-monitoreo)
9. [Solución de Problemas](#solución-de-problemas)
10. [Mejores Prácticas](#mejores-prácticas)

---

## Descripción General

El módulo de Automatización WooCommerce proporciona una integración completa entre Odoo 18 y tiendas WooCommerce. Permite la sincronización bidireccional de productos, pedidos, clientes e inventario, con flujos de trabajo automatizados y monitoreo en tiempo real.

### Características Principales

- **Sincronización Bidireccional de Productos** - Sincronizar productos entre Odoo y WooCommerce
- **Gestión de Pedidos** - Importar pedidos desde WooCommerce y actualizar estados
- **Sincronización de Clientes** - Mantener datos de clientes sincronizados entre sistemas
- **Gestión de Inventario** - Sincronización de inventario en tiempo real
- **Flujos de Trabajo Automatizados** - Sincronización programada con frecuencia configurable
- **Mapeo Avanzado** - Mapeo personalizado entre entidades de Odoo y WooCommerce
- **Informes Completos** - Registros detallados de sincronización y análisis
- **Soporte Multi-tienda** - Gestionar múltiples tiendas WooCommerce

---

## Instalación y Configuración

### Prerrequisitos

1. **Odoo 18** - Asegúrese de tener Odoo 18 instalado
2. **Tienda WooCommerce** - Tienda WooCommerce activa con API REST habilitada
3. **Credenciales API** - Clave de Consumidor y Secreto de WooCommerce
4. **Dependencias Requeridas**:
   - Python `requests>=2.25.1`
   - Python `woocommerce>=3.0.0`

### Pasos de Instalación

1. **Instalar el Módulo**
   - Vaya a Aplicaciones → Buscar "Automatización WooCommerce"
   - Haga clic en Instalar
   - Espere a que se complete la instalación

2. **Acceder al Módulo**
   - Navegue al menú WooCommerce en el menú principal
   - El módulo estará disponible en la sección WooCommerce

---

## Primeros Pasos

### Configuración Inicial

1. **Acceder al Panel de Control**
   - Vaya a WooCommerce → Panel de Control
   - Verá el panel principal con el estado de conexión

2. **Crear Configuración**
   - Haga clic en Configuración → Configuraciones
   - Haga clic en "Crear" para agregar su primera configuración de WooCommerce

3. **Configurar Conexión**
   - Ingrese los detalles de su tienda WooCommerce
   - Pruebe la conexión
   - Guarde la configuración

---

## Configuración

### Crear una Configuración de WooCommerce

#### Paso 1: Información Básica

1. **Nombre de Configuración**
   - Ingrese un nombre descriptivo (ej., "Tienda Principal", "Tienda de Prueba")
   - Esto ayuda a identificar diferentes configuraciones

#### Paso 2: Configuración de Conexión

1. **URL de la Tienda WooCommerce**
   - Ingrese la URL principal de su tienda (ej., `https://mitienda.com`)
   - Debe incluir el protocolo `https://`
   - Debe ser accesible desde su servidor Odoo

2. **Clave de Consumidor**
   - Se encuentra en WooCommerce → Configuración → Avanzado → API REST → Agregar Clave
   - Copie la Clave de Consumidor de la clave API generada

3. **Secreto del Consumidor**
   - Se encuentra en la misma ubicación que la Clave de Consumidor
   - Copie el Secreto del Consumidor de la clave API generada

4. **Versión de API**
   - Generalmente "wc/v3" para WooCommerce 3.0+
   - Déjelo como predeterminado si no está seguro

5. **Tiempo de Espera de Conexión**
   - Tiempo máximo para esperar respuestas de API
   - Predeterminado: 30 segundos

#### Paso 3: Configuración de Sincronización

1. **Opciones de Sincronización**
   - **Sincronizar Productos**: Habilitar para sincronizar información de productos
   - **Sincronizar Pedidos**: Habilitar para importar pedidos desde WooCommerce
   - **Sincronizar Clientes**: Habilitar para sincronizar datos de clientes
   - **Sincronizar Inventario**: Habilitar para mantener niveles de stock sincronizados

2. **Configuración de Auto Sincronización**
   - **Auto Sincronizar Productos**: Habilitar sincronización automática de productos
   - **Auto Sincronizar Pedidos**: Habilitar importación automática de pedidos
   - **Auto Sincronizar Clientes**: Habilitar sincronización automática de clientes
   - **Frecuencia de Sincronización**: Establecer con qué frecuencia ejecutar sincronización automática (ej., "1 hora", "30 minutos")

#### Paso 4: Probar Conexión

1. Haga clic en el botón "Probar Conexión" en el encabezado
2. Verifique que la conexión sea exitosa
3. Revise cualquier mensaje de error si la conexión falla

### Gestionar Múltiples Configuraciones

Puede crear múltiples configuraciones para:
- Diferentes tiendas WooCommerce
- Entornos de prueba y producción
- Diferentes estrategias de sincronización

---

## Panel de Control

### Descripción General

El panel de control proporciona una vista completa del estado de integración de WooCommerce y el rendimiento.

### Secciones Principales

#### 1. Estado de Conexión
- **Conectado**: Indicador verde cuando la conexión está activa
- **Error**: Indicador rojo cuando existen problemas de conexión
- **Desconectado**: Indicador amarillo cuando no se establece conexión

#### 2. Estadísticas de Sincronización
- **Productos Sincronizados**: Número total de productos sincronizados
- **Pedidos Sincronizados**: Número total de pedidos importados
- **Clientes Sincronizados**: Número total de clientes sincronizados
- **Errores de Sincronización**: Número de errores en las últimas 24 horas

#### 3. Acciones Rápidas
- **Importar Productos**: Abrir asistente de importación
- **Exportar Productos**: Abrir asistente de exportación
- **Asistente de Mapeo**: Configurar mapeos de datos
- **Configuración**: Acceder a configuraciones

#### 4. Actividad Reciente
- Cronología de actividades recientes de sincronización
- Indicadores de éxito/fallo
- Marcas de tiempo para cada actividad

---

## Sincronización

### Sincronización Manual

#### Sincronización de Productos

1. **Desde el Panel de Control**
   - Haga clic en la acción rápida "Importar Productos"
   - O vaya a WooCommerce → Herramientas → Asistente de Importación

2. **Configurar Importación**
   - Seleccionar configuración
   - Elegir opciones de importación
   - Establecer límites si es necesario
   - Hacer clic en "Iniciar Importación"

#### Sincronización de Pedidos

1. **Importar Pedidos**
   - Vaya a WooCommerce → Herramientas → Asistente de Importación
   - Seleccione la opción "Importar Pedidos"
   - Configure la configuración de importación

2. **Actualizar Estado de Pedidos**
   - Los pedidos se actualizan automáticamente con cambios de estado
   - Las actualizaciones manuales de estado también son compatibles

#### Sincronización de Clientes

1. **Sincronizar Clientes**
   - Use el asistente de importación para datos de clientes
   - Configure opciones de mapeo de clientes
   - Maneje clientes duplicados apropiadamente

### Sincronización Automatizada

#### Configurar Auto Sincronización

1. **Habilitar Auto Sincronización**
   - En la configuración, habilite las opciones de auto sincronización deseadas
   - Establezca la frecuencia de sincronización apropiada

2. **Monitorear Automatización**
   - Revise el panel de control para el estado de automatización
   - Revise los registros de sincronización para cualquier problema

#### Opciones de Frecuencia de Sincronización

- **Cada 5 minutos**: Para actualizaciones de alta frecuencia
- **Cada 15 minutos**: Enfoque equilibrado
- **Cada 30 minutos**: Frecuencia estándar
- **Cada hora**: Frecuencia más baja para sistemas estables
- **Diario**: Para actualizaciones menos críticas

---

## Herramientas y Asistentes

### Asistente de Importación

#### Propósito
Importar datos desde WooCommerce a Odoo

#### Características
- **Importación de Productos**: Importar productos con imágenes y variantes
- **Importación de Pedidos**: Importar pedidos con líneas de pedido
- **Importación de Clientes**: Importar información de clientes
- **Importación de Inventario**: Importar niveles de stock

#### Uso
1. Vaya a WooCommerce → Herramientas → Asistente de Importación
2. Seleccione configuración
3. Elija tipo de importación
4. Configure opciones
5. Inicie importación

### Asistente de Exportación

#### Propósito
Exportar datos desde Odoo a WooCommerce

#### Características
- **Exportación de Productos**: Exportar productos a WooCommerce
- **Exportación de Pedidos**: Exportar pedidos (si aplica)
- **Exportación de Clientes**: Exportar datos de clientes
- **Exportación de Inventario**: Actualizar niveles de stock

#### Uso
1. Vaya a WooCommerce → Herramientas → Asistente de Exportación
2. Seleccione configuración
3. Elija tipo de exportación
4. Configure opciones
5. Inicie exportación

### Asistente de Mapeo

#### Propósito
Configurar mapeos de datos entre Odoo y WooCommerce

#### Tipos de Mapeo
- **Categorías de Productos**: Mapear categorías de Odoo a categorías de WooCommerce
- **Estados de Pedidos**: Mapear estados de pedidos de Odoo a estados de WooCommerce
- **Métodos de Pago**: Mapear métodos de pago entre sistemas
- **Métodos de Envío**: Mapear métodos de envío
- **Grupos de Clientes**: Mapear grupos/segmentos de clientes
- **Atributos de Productos**: Mapear atributos y variantes de productos

#### Uso
1. Vaya a WooCommerce → Herramientas → Asistente de Mapeo
2. Seleccione configuración
3. Elija tipo de mapeo
4. Configure mapeos
5. Guarde mapeos

### Asistente de Prueba de Conexión

#### Propósito
Probar y verificar configuraciones de conexión de WooCommerce

#### Características
- **Prueba de Conexión**: Verificar credenciales de API
- **Información de Tienda**: Mostrar detalles de la tienda
- **Guardado de Configuración**: Guardar configuraciones que funcionan

#### Uso
1. Vaya a WooCommerce → Herramientas → Probar Conexión
2. Ingrese detalles de conexión
3. Pruebe conexión
4. Guarde configuración si es exitosa

---

## Informes y Monitoreo

### Registros de Sincronización

#### Acceso
- Vaya a WooCommerce → Informes → Registros de Sincronización

#### Información Disponible
- **Tipo de Sincronización**: Producto, Pedido, Cliente, Inventario
- **Operación**: Importación, Exportación, Actualización
- **Estado**: Éxito, Error, Advertencia, En Progreso
- **Tiempo**: Hora de inicio, hora de fin, duración
- **Registros**: Procesados, creados, actualizados, fallidos
- **Detalles de Error**: Mensajes de error específicos

#### Opciones de Filtrado
- **Estado**: Filtrar por éxito, error, advertencia
- **Tipo de Sincronización**: Filtrar por tipo de datos
- **Rango de Fechas**: Filtrar por período de tiempo
- **Configuración**: Filtrar por configuración específica

### Informes de Sincronización

#### Acceso
- Vaya a WooCommerce → Informes → Informe de Sincronización

#### Tipos de Informes
- **Informes de Rendimiento**: Velocidad y eficiencia de sincronización
- **Informes de Errores**: Análisis detallado de errores
- **Informes de Tendencias**: Patrones históricos de sincronización
- **Informes de Configuración**: Estado de configuraciones y mapeos

---

## Solución de Problemas

### Problemas Comunes

#### Problemas de Conexión

**Problema**: No se puede conectar a la tienda WooCommerce
**Soluciones**:
1. Verificar que la URL de la tienda sea correcta y accesible
2. Verificar que la Clave de Consumidor y Secreto sean válidos
3. Asegurar que la API REST esté habilitada en WooCommerce
4. Verificar conectividad de firewall/red

#### Fallos de Sincronización

**Problema**: La sincronización falla con errores
**Soluciones**:
1. Revisar registros de sincronización para mensajes de error específicos
2. Verificar que el mapeo de datos sea correcto
3. Asegurar que los campos requeridos estén poblados
4. Verificar registros duplicados

#### Problemas de Rendimiento

**Problema**: Sincronización lenta o timeouts
**Soluciones**:
1. Aumentar tiempo de espera de conexión en la configuración
2. Reducir tamaños de lotes de sincronización
3. Programar sincronizaciones durante horas de menor actividad
4. Verificar recursos del servidor

### Mensajes de Error

#### "Credenciales de API Inválidas"
- Verificar Clave de Consumidor y Secreto
- Regenerar credenciales de API si es necesario
- Verificar permisos de API en WooCommerce

#### "URL de Tienda No Accesible"
- Verificar que la URL sea correcta
- Verificar conectividad de red
- Asegurar que se use HTTPS

#### "Mapeo de Datos Requerido"
- Configurar mapeos usando el Asistente de Mapeo
- Verificar que todos los mapeos requeridos estén configurados
- Verificar mapeos de campos faltantes

### Obtener Ayuda

#### Recursos de Soporte
- **Documentación**: Esta guía de usuario
- **Registros**: Revisar registros de sincronización para información detallada de errores
- **Configuración**: Verificar que todas las configuraciones sean correctas
- **Soporte ECOSIRE**: Contactar info@ecosire.com

#### Información de Depuración
Al reportar problemas, proporcione:
1. Mensajes de error de los registros de sincronización
2. Configuraciones (sin datos sensibles)
3. Versión de WooCommerce y configuración
4. Versión de Odoo y detalles del entorno

---

## Mejores Prácticas

### Mejores Prácticas de Configuración

1. **Usar Nombres Descriptivos**
   - Nombrar configuraciones claramente (ej., "Tienda de Producción", "Entorno de Prueba")
   - Incluir URL de tienda o propósito en el nombre

2. **Credenciales de API Seguras**
   - Almacenar credenciales de forma segura
   - Usar permisos de lectura/escritura apropiadamente
   - Rotar claves de API regularmente

3. **Probar Antes de Producción**
   - Siempre probar configuraciones en un entorno de prueba
   - Verificar mapeos antes de sincronización completa
   - Comenzar con conjuntos de datos pequeños

### Mejores Prácticas de Sincronización

1. **Comenzar Pequeño**
   - Comenzar con pocos productos o pedidos
   - Aumentar volumen de sincronización gradualmente
   - Monitorear rendimiento y errores

2. **Programar Apropiadamente**
   - Evitar horas pico de negocio para sincronizaciones grandes
   - Usar frecuencias de sincronización apropiadas
   - Monitorear rendimiento de sincronización

3. **Monitoreo Regular**
   - Revisar registros de sincronización regularmente
   - Monitorear errores y advertencias
   - Revisar estadísticas de sincronización

### Mejores Prácticas de Gestión de Datos

1. **Respaldo Antes de Cambios Importantes**
   - Respaldo de datos antes de importaciones/exportaciones grandes
   - Probar cambios en entorno no productivo
   - Tener planes de rollback listos

2. **Manejar Duplicados**
   - Configurar estrategias de manejo de duplicados
   - Usar identificadores únicos para mapeo
   - Limpieza regular de registros duplicados

3. **Mantener Calidad de Datos**
   - Validación regular de datos sincronizados
   - Monitorear inconsistencias de datos
   - Implementar verificaciones de calidad de datos

### Optimización de Rendimiento

1. **Optimizar Frecuencia de Sincronización**
   - Equilibrar entre tiempo real y rendimiento
   - Usar tamaños de lotes apropiados
   - Monitorear recursos del servidor

2. **Mapeos Eficientes**
   - Usar estrategias de mapeo eficientes
   - Minimizar mapeos de campos innecesarios
   - Optimizar reglas de transformación de datos

3. **Gestión de Recursos**
   - Monitorear uso de CPU y memoria del servidor
   - Optimizar consultas de base de datos
   - Usar timeouts apropiados

---

## Características Avanzadas

### Mapeos Personalizados

#### Crear Mapeos Personalizados
1. Usar el Asistente de Mapeo
2. Definir mapeos de campos personalizados
3. Establecer reglas de transformación
4. Probar mapeos exhaustivamente

#### Estrategias de Mapeo
- **Mapeo Directo**: Mapeo simple de campo a campo
- **Mapeo de Transformación**: Reglas de transformación de datos
- **Mapeo Condicional**: Mapeo basado en reglas
- **Mapeo de Valor Predeterminado**: Valores de respaldo

### Gestión Multi-tienda

#### Gestionar Múltiples Tiendas
1. Crear configuraciones separadas para cada tienda
2. Usar nombres descriptivos para fácil identificación
3. Monitorear cada tienda independientemente
4. Configurar mapeos específicos por tienda

#### Mejores Prácticas para Multi-tienda
- **Gestión Centralizada**: Usar Odoo como punto de gestión central
- **Configuraciones Específicas por Tienda**: Configurar cada tienda apropiadamente
- **Monitoreo Independiente**: Monitorear cada tienda por separado
- **Nomenclatura Consistente**: Usar convenciones de nomenclatura consistentes

---

## Conclusión

El módulo de Automatización WooCommerce proporciona capacidades de integración poderosas entre Odoo y WooCommerce. Siguiendo esta guía de usuario y las mejores prácticas, puede gestionar efectivamente sus operaciones de comercio electrónico con sincronización automatizada y monitoreo completo.

### Soporte y Actualizaciones

Para soporte, actualizaciones y características adicionales:
- **Sitio Web**: https://www.ecosire.com/
- **Email**: info@ecosire.com
- **Documentación**: Revisar guías y tutoriales actualizados

### Información de Versión

- **Versión del Módulo**: 18.0.1.0.0
- **Compatibilidad con Odoo**: Odoo 18.0+
- **Compatibilidad con WooCommerce**: WooCommerce 3.0+
- **Última Actualización**: Agosto 2024

---

*Esta guía de usuario es proporcionada por ECOSIRE (PRIVATE) LIMITED. Para soporte técnico y preguntas, por favor contacte info@ecosire.com.*
