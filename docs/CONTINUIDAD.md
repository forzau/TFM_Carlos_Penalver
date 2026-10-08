# Continuar en otro equipo o conversación

## Si se utiliza la carpeta sincronizada con OneDrive

1. Terminar y guardar el trabajo en el equipo de origen. Actualizar los archivos
   de `contexto/` y subir a GitHub los cambios que se quieran conservar en el historial.
2. Esperar a que OneDrive complete la sincronización antes de cambiar de equipo.
3. Abrir la carpeta del TFM en el otro equipo y comprobar que los archivos de
   `Fuentes/` necesarios estén descargados y disponibles localmente.
4. Trabajar desde un solo equipo a la vez sobre esta carpeta, incluida su carpeta
   `.git`, para evitar cambios simultáneos durante la sincronización.
5. Comprobar el estado del repositorio y leer los archivos de contexto.

```sh
git status
git remote -v
```

Con la copia limpia, actualizarla desde GitHub:

```sh
git pull --ff-only
```

Si aparecen cambios locales o conflictos de sincronización, revisarlos antes de
continuar. Conservar el trabajo pendiente; no usar comandos de descarte para
resolverlos automáticamente.

## Si se parte de una copia nueva del repositorio

Tener Git instalado y autenticarse con la propia cuenta para poder subir cambios.
Desde el directorio que vaya a contener el proyecto:

```sh
git clone https://github.com/forzau/TFM_Carlos_Penalver.git TFM
cd TFM
```

Después, recuperar `Fuentes/` desde OneDrive manteniendo sus nombres y estructura,
y crear `resultados/` si no estuviera disponible. GitHub no almacena los datos originales
ni las salidas pesadas. Consultar `docs/FUENTES.md` para contrastar el inventario.

La autenticación de GitHub y las herramientas instaladas dependen de cada equipo;
no guardar contraseñas ni tokens en el proyecto.

## Al iniciar una conversación nueva

Pedir al asistente que lea `AGENTS.md` y los tres documentos de `contexto/`.
Estos archivos recogen lo confirmado, los pendientes, las decisiones y el próximo paso.

## Al cerrar una sesión de trabajo

1. Actualizar el estado y las decisiones que correspondan.
2. Revisar los cambios y seleccionar los archivos concretos que se van a versionar.
3. Revisar lo seleccionado, guardar una versión y subirla a GitHub.

```sh
git status
git diff
git add <archivos-revisados>
git diff --cached
git commit -m "Descripción del trabajo realizado"
git push origin main
```

Sustituir `<archivos-revisados>` por las rutas concretas. Mantener `Fuentes/` y
las salidas pesadas fuera de Git; OneDrive las sincroniza por separado.
