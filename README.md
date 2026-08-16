# Minecraft Bot Control — Prototipo

Controlador de hasta **30 bots de Minecraft Java Edition** desde una interfaz
grafica moderna en Python (PySide6), con un puente Node.js/mineflayer minimo
que habla el protocolo del juego. Toda la logica de alto nivel (formaciones,
movimiento, seguimiento, chat, comandos, y la que tu anyadas despues) vive en
Python.

---

## 1. Que hace el proyecto

- Conecta hasta 30 bots a tu servidor de Minecraft **simultaneamente** (sin
  esperas artificiales entre bots).
- Muestra el estado en vivo de cada bot (posicion, vida, hambre, tarea) en
  una tabla que se actualiza sin congelar la interfaz.
- Botones para **REUNIR**, **FORMAR** (cuadricula NxM configurable, por
  defecto 6x5 = 30), **SEGUIR** (jugador / bot lider / coordenadas),
  movimiento basico, **SALTAR** (sincronizado) y **MIRAR** / sincronizar
  cabezas.
- Caja de chat/comandos que distingue automaticamente entre un mensaje de
  chat y un comando de servidor (`/comando`), con un selector de destino
  (todos / un bot / un grupo seleccionado) y un atajo `!bots <texto>` que
  siempre va a todos los bots.
- API Python sencilla (`manager.broadcast_chat(...)`,
  `manager.get_bot(1).jump()`, etc.) para que puedas seguir construyendo
  encima sin tocar la GUI.

**No** es un framework completo de automatizacion (mineria, combate, IA...).
Es una base limpia y extensible para que tu anyadas eso despues.

---

## 2. Arquitectura

### 2.1 Decision tecnologica: Python + Node.js/mineflayer

Antes de escribir codigo se compararon las alternativas para hablar el
protocolo de Minecraft Java Edition desde Python:

| Opcion | Estado | Veredicto |
|---|---|---|
| **pyCraft** | Proyecto en gran medida abandonado, sin soporte para versiones modernas del protocolo, sin API de movimiento/fisica de alto nivel. | Descartado: no es fiable para un prototipo que debe funcionar hoy. |
| **mineflayer (Node.js)** | Activamente mantenido, soporta versiones recientes de Java Edition, tiene fisica de movimiento, deteccion de entidades/jugadores, chat, eventos ricos (`spawn`, `health`, `move`, etc.), y un ecosistema de plugins (pathfinder, pvp, etc.). | **Elegido** como motor de conexion real al juego. |
| **Baritone** | Es un mod/cliente de Java pensado para *un* jugador con pathfinding avanzado, no una libreria pensada para orquestar 30 bots headless desde otro lenguaje. | Descartado para esta base (se puede explorar en el futuro solo para pathfinding). |
| **Otras (node-minecraft-protocol puro, etc.)** | mineflayer ya se construye sobre `node-minecraft-protocol` y anyade la capa de alto nivel (fisica, entidades) que necesitamos; usar el protocolo a pelo implicaria reimplementar eso. | Descartado por redundante. |

**No existe hoy una solucion 100% Python suficientemente madura** para
controlar el movimiento/fisica de 30 bots en Minecraft Java moderno con la
fiabilidad de mineflayer. Por eso se usa un **bridge Node.js minimo**
(`bridge/bridge.js`, ~350 lineas) cuyo unico trabajo es hablar con
mineflayer y reenviar eventos/ordenes por WebSocket. Cumpliendo lo pedido:

- Python es el controlador principal, la GUI, el `BotManager`, las
  formaciones, el movimiento de alto nivel y el sistema de comandos.
- Node.js se reduce al minimo imprescindible: crear/cerrar conexiones
  mineflayer, mandar `chat()`, y ejecutar primitivas de movimiento
  (`move_to`, `jump`, `look_at`, `follow`) que Python le ordena.
- El bridge **no** contiene ninguna logica de "que hacer": no sabe que es
  una formacion, ni un grupo, ni un lider. Solo ejecuta ordenes puntuales.

### 2.2 Concurrencia elegida

Se evaluaron `threading`, `multiprocessing` y `asyncio`:

- **`multiprocessing`** se descarto: 30 procesos serian un desperdicio de
  recursos para bots que solo intercambian mensajes JSON pequenyos, y
  complicaria mucho compartir estado con la GUI.
- **`threading`** puro en Python para 30 conexiones WebSocket seria
  ineficiente comparado con IO asincrono, y anyade complejidad de locks.
- **`asyncio`** es la eleccion natural para *muchas conexiones de red
  concurrentes* con poco overhead. Se usa en un **unico hilo secundario**
  dedicado (`minecraft/adapter.py::_AsyncLoopThread`) que corre su propio
  event loop de asyncio, separado del hilo de la GUI de Qt.

Cuando el usuario pulsa "CONECTAR TODOS", `BotManager.connect_all()` (que se
ejecuta en el hilo de la GUI) llama a `bridge.send(...)` para cada uno de los
30 bots. Cada llamada usa `asyncio.run_coroutine_threadsafe(...)` para
encolar el envio en el hilo asincrono **sin bloquear** el hilo de Qt ni
esperar a que el bot anterior termine. Del lado de Node, cada mensaje
`connect` dispara `mineflayer.createBot(...)`, que es no bloqueante: los 30
intentos de conexion TCP se lanzan practicamente a la vez.

Los eventos que llegan del bridge (posicion, vida, chat, errores) se reciben
en el hilo asincrono y se reenvian a la GUI mediante **senales Qt**
(`Signal`), que son thread-safe para cruzar de un hilo a otro. La GUI nunca
ejecuta directamente codigo de red.

### 2.3 Arbol de archivos

```
minecraft_bot/
│
├── main.py                     # Punto de entrada de la app
├── config.py                   # Config centralizada (.env)
├── requirements.txt
├── README.md
├── .env.example
│
├── gui/
│   ├── main_window.py           # Ventana principal + tema oscuro
│   ├── control_panel.py         # Servidor + Reunir/Formar/Seguir/Mover/Saltar/Mirar
│   ├── bot_panel.py             # Tabla de estado en vivo de los bots
│   ├── command_panel.py         # Chat / comandos + selector de destino
│   ├── log_panel.py             # Panel de LOG con color por nivel
│   └── dialogs.py               # (anyadido) dialogos de Reunir/Formar/Seguir/Mirar
│
├── bots/
│   ├── minecraft_bot.py         # Clase MinecraftBot
│   ├── bot_manager.py           # BotManager (orquestador central)
│   ├── bot_state.py             # Enum BotState
│   └── bot_group.py             # BotGroup (subconjuntos de bots)
│
├── controllers/
│   ├── movement_controller.py   # Movimiento de alto nivel (abstraccion)
│   ├── formation_controller.py  # Calculo matematico de formaciones NxM
│   ├── follow_controller.py     # Seguir jugador/bot/coordenadas
│   ├── look_controller.py       # yaw/pitch, mirar, sincronizar cabezas
│   └── command_controller.py    # Parseo chat vs comando, !bots
│
├── minecraft/
│   └── adapter.py                # BridgeClient: WebSocket asincrono <-> bridge Node.js
│
├── core/
│   ├── events.py                 # EventBus simple (pub/sub)
│   ├── logger.py                 # Logger a consola + archivo
│   └── exceptions.py             # Excepciones propias
│
├── bridge/                       # (anyadido) puente Node.js/mineflayer minimo
│   ├── package.json
│   └── bridge.js
│
└── tests/
    ├── conftest.py                # Fixtures + DummyBridge (sin red real)
    ├── test_bot_manager.py
    ├── test_formation.py
    └── test_config.py
```

**Cambios respecto al arbol propuesto en el prompt:**
- Se anyadio `bridge/` (Node.js) porque, tras el analisis de la seccion 2.1,
  se necesita un proceso Node.js minimo para hablar con mineflayer.
- Se anyadio `gui/dialogs.py` para mantener los formularios emergentes
  (Reunir/Formar/Seguir/Mirar) separados de `control_panel.py`.
- Se anyadio `tests/conftest.py` con un `DummyBridge` para poder testear
  `BotManager` sin abrir conexiones de red reales.

---

## 3. Requisitos

- **Python 3.10+** (recomendado 3.11 o 3.12).
- **Node.js 18+** (LTS recomendado) — solo para el bridge.
- **Java** no es necesario en tu maquina para ejecutar el prototipo (el
  bridge no necesita Java); solo lo necesitas si tu servidor de pruebas es
  local y corre en la misma maquina.
- Un servidor de Minecraft Java Edition de pruebas (ver seccion 6).

---

## 4. Instalacion (Windows / PowerShell)

Abre **PowerShell** en la carpeta `minecraft_bot/`.

### 4.1 Entorno Python

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4.2 Bridge Node.js

Instala Node.js 18 LTS o superior desde https://nodejs.org (instalador MSI,
marca la opcion de anyadirlo al PATH). Comprueba la version:

```powershell
node -v
npm -v
```

Instala las dependencias del bridge:

```powershell
cd bridge
npm install
cd ..
```

### 4.3 Copia la configuracion

```powershell
Copy-Item .env.example .env
```

Edita `.env` con un editor de texto y ajusta `MINECRAFT_HOST`,
`MINECRAFT_PORT`, etc. si hace falta (ver seccion 5).

---

## 5. Configuracion

Todo se controla desde `.env` (ver `.env.example`):

```
MINECRAFT_HOST=127.0.0.1
MINECRAFT_PORT=25565
MINECRAFT_VERSION=1.20.4
MINECRAFT_AUTH=offline

BOT_COUNT=30
BOT_PREFIX=Bot_

FORMATION_COLUMNS=6
FORMATION_ROWS=5
FORMATION_SPACING=1.5

BRIDGE_HOST=127.0.0.1
BRIDGE_PORT=8765
```

No se guarda ninguna contrasenya en el codigo: para servidores
`offline-mode`, mineflayer no necesita contrasenya (usa `auth=offline`).
El prototipo **no crea cuentas automaticamente** ni implementa
autenticacion Microsoft en bucle para 30 bots (ver seccion siguiente).

---

## 6. Configuracion del servidor de Minecraft

Diferencias importantes entre modos de autenticacion:

- **Servidor local/offline-mode** (`online-mode=false` en `server.properties`):
  cualquier nombre de usuario es aceptado sin verificarlo contra los
  servidores de Mojang/Microsoft. Es el modo **recomendado para este
  prototipo**: puedes crear 30 nombres de bot (`Bot_01`...`Bot_30`) sin
  necesitar 30 cuentas reales.
- **Servidor online-mode** (`online-mode=true`, el modo por defecto de un
  servidor "normal"): el servidor verifica cada conexion contra los
  servidores de Mojang/Microsoft. Para conectar un bot aqui necesitarias una
  cuenta de Microsoft real y valida por cada bot, lo cual **no es practico
  ni deseable para 30 bots automatizados** y esta fuera del alcance de este
  prototipo.
- **Autenticacion Microsoft** (`auth: "microsoft"` en mineflayer): abre un
  flujo interactivo de login (codigo por navegador) por cada bot. El bridge
  lo soporta como opcion (`MINECRAFT_AUTH=microsoft`) pero **no esta pensado
  para 30 bots simultaneos**: usalo solo si necesitas 1-2 bots contra un
  servidor online-mode y estas dispuesto a autenticarlos manualmente.

Para el prototipo, monta tu propio servidor de pruebas (por ejemplo Paper o
Vanilla) con `online-mode=false` en `server.properties`.

---

## 7. Como ejecutar

Necesitas **dos procesos** corriendo a la vez: el bridge Node.js y la app
Python.

**Terminal 1 — bridge:**

```powershell
cd bridge
npm start
```

Deberias ver: `Bridge escuchando en ws://127.0.0.1:8765`

**Terminal 2 — app Python:**

```powershell
.venv\Scripts\Activate.ps1
python main.py
```

Se abrira la ventana "MINECRAFT BOT CONTROL".

---

## 8. Como conectar los 30 bots

1. En el panel **SERVIDOR**, escribe la IP y el puerto de tu servidor de
   pruebas, y el numero de bots (hasta 30).
2. Pulsa **🟢 CONECTAR TODOS**.
3. Los 30 bots intentan conectarse simultaneamente. La tabla **BOTS** y el
   panel **LOG** muestran el resultado de cada uno individualmente
   (conectado, o el motivo del error) sin que un fallo bloquee a los demas.
4. Pulsa **🔴 DESCONECTAR TODOS** para cerrar todas las conexiones.

---

## 9. Como utilizar REUNIR

Pulsa **📍 REUNIR** y elige:

- **Alrededor del jugador**: escribe el nombre del jugador; los bots
  seleccionados empiezan a seguirlo (el bridge recalcula su posicion en
  tiempo real).
- **En coordenadas**: introduce X, Y, Z; los bots se agrupan en una
  cuadricula compacta centrada en ese punto.
- **Alrededor de un bot**: elige un bot de la lista como ancla.

Si no has seleccionado ninguna fila en la tabla BOTS, se aplica a todos.

---

## 10. Como utilizar FORMAR

Pulsa **🛡 FORMAR** e indica columnas, filas, separacion, orientacion y
ancla (X, Y, Z). Por defecto es 6 columnas x 5 filas = 30 bots. El calculo
de posiciones es completamente generico (funciona igual para 5x6, 3x10,
10x3, etc.) — ver `controllers/formation_controller.py`.

---

## 11. Como utilizar SEGUIR

Pulsa **👣 SEGUIR** y elige:

- Seguir a un **jugador** (por nombre).
- Seguir a un **bot lider** (los demas bots seleccionados lo siguen).
- Seguir unas **coordenadas fijas**.

El seguimiento es continuo: el bridge recalcula la posicion del objetivo
varias veces por segundo mientras el bot camina hacia el.

---

## 12. Como utilizar SALTAR

Pulsa **⏫ SALTAR**: todos los bots (o los seleccionados en la tabla) reciben
la orden de salto casi al mismo tiempo, de forma coordinada.

---

## 13. Como utilizar MIRAR

Pulsa **👁 MIRAR** y elige "mirar al centro del grupo" o "mirar a
coordenadas". El boton **🔄 SINCRONIZAR CABEZAS** hace que todos los bots
orienten la cabeza hacia el mismo punto de referencia.

---

## 14. Como enviar chat

En el panel **CHAT / COMANDOS**, escribe un mensaje normal (que no empiece
por `/`), elige el destino (TODOS / GRUPO seleccionado / un bot concreto) y
pulsa **ENVIAR**. Tambien puedes usar el atajo `!bots <mensaje>`, que
siempre envia a todos los bots sin importar el selector.

---

## 15. Como enviar comandos

Escribe un texto que empiece por `/` (por ejemplo `/spawn` o
`/tp 100 64 -200`) y pulsa **ENVIAR**. El programa distingue
automaticamente comando de chat por el prefijo `/`. Si el bot no tiene
permisos en el servidor, el propio servidor respondera con un error, que
aparecera en el panel LOG como mensaje de chat — el prototipo **no intenta
saltarse permisos** de ninguna forma.

---

## 16. Como anyadir nuevos controladores

1. Crea un archivo en `controllers/`, por ejemplo `combat_controller.py`.
2. Define una clase con metodos que reciban una lista de `MinecraftBot` y
   deleguen en `bot.manager.bridge.send({...})` para las acciones que
   necesiten hablar con Minecraft, o en los controladores existentes
   (`MovementController`, `LookController`) para reutilizar movimiento.
3. Instancialo en `BotManager.__init__` (junto a `self.movement`,
   `self.formation`, etc.) y expon un metodo de alto nivel en `BotManager`
   si quieres usarlo desde la GUI o desde `manager.mi_controlador...`.
4. Si necesitas una primitiva nueva del lado de Minecraft que mineflayer no
   cubre con lo ya expuesto, anyade un nuevo `case` en el switch de
   `bridge/bridge.js` y su mensaje de respuesta correspondiente.

---

## 17. Como anyadir tus propias clases

`MinecraftBot` y `BotManager` estan pensados para extenderse sin modificar
el nucleo. Ejemplo:

```python
# mis_clases/mi_logica.py
class MyCustomBotLogic:
    def __init__(self, manager):
        self.manager = manager

    def update(self):
        for bot in self.manager.all_bots():
            if bot.health < 10:
                bot.send_chat(f"{bot.name} necesita ayuda!")
```

```python
# en main.py, despues de crear el manager:
from mis_clases.mi_logica import MyCustomBotLogic

my_logic = MyCustomBotLogic(manager)
# ejecutalo periodicamente con un QTimer, por ejemplo:
from PySide6.QtCore import QTimer
timer = QTimer()
timer.timeout.connect(my_logic.update)
timer.start(1000)
```

Tambien puedes suscribirte a eventos sin tocar el nucleo usando el
`EventBus` de `core/events.py`.

---

## 18. Problemas comunes

- **"No se pudo conectar al bridge"**: asegurate de que
  `cd bridge && npm start` esta corriendo ANTES de lanzar `python main.py`.
- **Todos los bots dan `ECONNREFUSED`**: revisa `MINECRAFT_HOST` /
  `MINECRAFT_PORT` y que el servidor de Minecraft este realmente escuchando
  (¿firewall? ¿el server aun esta arrancando?).
- **Los bots se conectan pero el servidor los expulsa (`kicked`)**: revisa
  `online-mode` en `server.properties` (ver seccion 6) y la version
  configurada en `MINECRAFT_VERSION` (debe coincidir o ser compatible con la
  del servidor).
- **La GUI se queda en blanco/no responde al arrancar**: la primera vez que
  PySide6 se importa puede tardar unos segundos; si persiste, revisa
  `logs/app.log`.
- **`npm install` falla en Windows compilando dependencias nativas**:
  instala las "Herramientas de compilacion de C++ de Visual Studio" o usa
  una version de Node.js LTS reciente (18+), que suele traer binarios
  precompilados para las dependencias de mineflayer.

---

## 19. Limitaciones actuales

- El movimiento (`move_to`, `follow`) es una caminata simple mirando hacia
  el objetivo (sin evitar obstaculos complejos ni pathfinding real). Es una
  base preparada para integrar un pathfinder mas adelante.
- No hay deteccion de mobs, inventario, combate, mineria, tala ni
  construccion todavia — deliberadamente, segun lo pedido.
- El seguimiento de "jugador" depende de que mineflayer vea al jugador
  dentro de su rango de vision/carga de chunks.
- No se han implementado mecanismos para evadir anti-cheat, ni es un
  objetivo del proyecto.

---

## 20. Proximos pasos sugeridos

```
REUNIR -> FORMAR -> SEGUIR -> MOVIMIENTO -> PATHFINDING -> COMBATE ->
MINERIA -> TALA -> CONSTRUCCION -> IA
```

Los siguientes controladores ya tienen su hueco previsto en la arquitectura
(solo hay que anyadir el archivo en `controllers/` y las primitivas que
falten en `bridge/bridge.js`): `CombatController`, `MiningController`,
`WoodcuttingController`, `BuildingController`, `FarmingController`,
`InventoryController`, `TaskManager`, `Pathfinder`, `Perception`,
`MobDetection`, `AIController`.
