"use strict";

const obtener = (id) => document.getElementById(id);
const mapa = obtener("mapa");
const capas = obtener("municipios");
const formulario = obtener("filtros");
const busqueda = obtener("busqueda");
const provincia = obtener("provincia");
const perfil = obtener("perfil");
const lista = obtener("lista");
const sugerencias = obtener("sugerencias");
const tooltip = obtener("tooltip");
const formato = new Intl.NumberFormat("es-ES", { useGrouping: "always" });
const ordenar = new Intl.Collator("es-ES");
const SVG = "http://www.w3.org/2000/svg";
const SIN_PERFIL = "sin-perfil";
const pantallaEstrecha = window.matchMedia("(max-width: 760px)");

let datos;
let visibles = [];
let indiceActivo = -1;
let seleccion = null;
let vista;
let vistaRegional;
let arrastre = null;
let evitarClick = false;
const recintos = new Map();

function normalizar(texto) {
  return texto.toLocaleLowerCase("es")
    .normalize("NFD").replace(/\p{Diacritic}/gu, "")
    .replace(/[^a-z0-9]+/g, " ").trim();
}

function nombreMunicipio(nombre) {
  return nombre.split("/").map((variante) => variante.replace(
    /^(.+), (el|la|els|les|los|las|l')$/i,
    (_, resto, articulo) => articulo.charAt(0).toUpperCase() + articulo.slice(1)
      + (articulo.endsWith("'") ? "" : " ") + resto,
  )).join("/");
}

function etiqueta(municipio) {
  return datos.perfiles[municipio.perfil] ?? "Sin perfil";
}

function grupo(municipio) {
  return municipio.perfil ?? SIN_PERFIL;
}

function punto(perfilMunicipal) {
  const marca = document.createElement("span");
  marca.className = "punto";
  marca.dataset.perfil = perfilMunicipal;
  marca.setAttribute("aria-hidden", "true");
  return marca;
}

function establecerVista(nuevaVista) {
  vista = nuevaVista;
  mapa.setAttribute("viewBox", [vista.x, vista.y, vista.ancho, vista.alto].join(" "));
  obtener("acercar").disabled = vista.alto <= vistaRegional.alto / 20;
  obtener("alejar").disabled = vista.alto >= vistaRegional.alto;
  tooltip.hidden = true;
}

function encuadrarRegion() {
  const limites = datos.municipios.map((municipio) => municipio.limites);
  const izquierda = Math.min(...limites.map(([x]) => x));
  const arriba = Math.min(...limites.map(([, y]) => y));
  const derecha = Math.max(...limites.map(([, , x]) => x));
  const abajo = Math.max(...limites.map(([, , , y]) => y));
  const ancho = derecha - izquierda;
  const alto = abajo - arriba;
  if (!mapa.clientWidth || !mapa.clientHeight) return;

  const proporcion = mapa.clientWidth / mapa.clientHeight;
  const altoVista = Math.max(alto, ancho / proporcion) * 1.13;
  const anchoVista = altoVista * proporcion;
  const desplazamiento = proporcion > 1.15 ? (anchoVista - ancho) * 0.15 : 0;
  vistaRegional = {
    x: (izquierda + derecha - anchoVista) / 2 - desplazamiento,
    y: (arriba + abajo - altoVista) / 2,
    ancho: anchoVista,
    alto: altoVista,
  };
  const mar = obtener("mar");
  mar.setAttribute("x", izquierda + ancho * 1.08);
  mar.setAttribute("y", arriba + alto * 0.60);
  establecerVista(vistaRegional);
}

function zoom(factor) {
  const alto = Math.min(vistaRegional.alto, Math.max(vistaRegional.alto / 20, vista.alto * factor));
  if (alto === vistaRegional.alto) {
    establecerVista(vistaRegional);
    return;
  }
  const ancho = alto * vista.ancho / vista.alto;
  establecerVista({
    x: vista.x + (vista.ancho - ancho) / 2,
    y: vista.y + (vista.alto - alto) / 2,
    ancho,
    alto,
  });
}

function desplazarSiOculto(municipio) {
  const [x1, y1, x2, y2] = municipio.limites;
  const x = (x1 + x2) / 2;
  const y = (y1 + y2) / 2;
  if (x < vista.x || x > vista.x + vista.ancho || y < vista.y || y > vista.y + vista.alto) {
    establecerVista({ ...vista, x: x - vista.ancho / 2, y: y - vista.alto / 2 });
  }
}

function construirMapa() {
  const fragmento = document.createDocumentFragment();
  for (const municipio of datos.municipios) {
    const recinto = document.createElementNS(SVG, "path");
    recinto.setAttribute("d", municipio.trazado);
    recinto.dataset.perfil = grupo(municipio);
    recinto.classList.add("municipio");
    recinto.addEventListener("pointermove", (evento) => {
      if (evento.pointerType !== "mouse" || arrastre?.movido) return;
      obtener("tooltip-nombre").textContent = municipio.nombre;
      obtener("tooltip-perfil").textContent = etiqueta(municipio);
      tooltip.hidden = false;
      const panel = mapa.parentElement.getBoundingClientRect();
      const x = evento.clientX - panel.left + 14;
      const y = evento.clientY - panel.top + 14;
      tooltip.style.left = Math.max(8, Math.min(x, panel.width - tooltip.offsetWidth - 8)) + "px";
      tooltip.style.top = Math.max(8, Math.min(y, panel.height - tooltip.offsetHeight - 8)) + "px";
    });
    recinto.addEventListener("pointerleave", () => { tooltip.hidden = true; });
    recinto.addEventListener("click", () => {
      if (evitarClick) return;
      seleccionar(municipio);
      mostrarFichaEnMovil();
    });
    recintos.set(municipio.codigo_municipio, recinto);
    fragmento.append(recinto);
  }
  capas.append(fragmento);
  new ResizeObserver(() => encuadrarRegion()).observe(mapa);
  encuadrarRegion();
}

function avisoMunicipal(municipio) {
  const mensajes = [];
  if (municipio.perfil === null) {
    mensajes.push("Municipio excluido de la segmentación. Su parque domiciliado se consideró poco representativo de la demanda local.");
  }
  const pendientes = municipio.instalaciones_pendientes_relacionadas;
  if (pendientes === 1) mensajes.push("Una instalación relacionada tiene su asignación municipal pendiente.");
  if (pendientes > 1) mensajes.push(`${formato.format(pendientes)} instalaciones relacionadas tienen su asignación municipal pendiente.`);
  if (municipio.instalaciones_ausentes_relacionadas > 0) {
    mensajes.push("Hay instalaciones relacionadas con diferencias entre las copias de recarga.");
  }
  if (municipio.hay_incertidumbre_sin_localizar) {
    mensajes.push("Parte de la información de recarga está pendiente de localizar.");
  }
  return mensajes.join(" ");
}

function mostrarMedida(id, valor) {
  const campo = obtener(id);
  campo.textContent = valor == null ? "Dato no disponible" : formato.format(valor);
  campo.classList.toggle("sin-dato", valor == null);
}

function seleccionar(municipio) {
  if (seleccion) recintos.get(seleccion.codigo_municipio).classList.remove("seleccionado");
  seleccion = municipio;
  obtener("ficha-inicio").hidden = Boolean(seleccion);
  obtener("ficha").hidden = !seleccion;
  if (!seleccion) {
    obtener("anuncio-ficha").textContent = "Ficha cerrada.";
    return;
  }

  const recinto = recintos.get(municipio.codigo_municipio);
  recinto.classList.add("seleccionado");
  capas.append(recinto);
  desplazarSiOculto(municipio);

  obtener("ficha-nombre").textContent = municipio.nombre;
  obtener("ficha-provincia").textContent = datos.provincias[municipio.codigo_provincia];
  const perfilFicha = obtener("ficha-perfil");
  perfilFicha.dataset.perfil = grupo(municipio);
  perfilFicha.lastElementChild.textContent = etiqueta(municipio);
  mostrarMedida("ficha-vehiculos", municipio.vehiculos_distintivo_0);
  mostrarMedida("ficha-puntos", municipio.puntos_con_municipio_admitido);
  mostrarMedida("ficha-poblacion", municipio.poblacion_total);
  const aviso = avisoMunicipal(municipio);
  obtener("ficha-aviso").textContent = aviso;
  obtener("ficha-aviso").hidden = !aviso;
  obtener("filtrar-perfil").hidden = municipio.perfil === null;
  obtener("anuncio-ficha").textContent = `Ficha de ${municipio.nombre}. ${etiqueta(municipio)}.`;
}

function marcarSugerencia(indice, desplazar = false) {
  lista.children[indiceActivo]?.setAttribute("aria-selected", "false");
  indiceActivo = indice;
  const opcion = lista.children[indice];
  if (opcion) {
    opcion.setAttribute("aria-selected", "true");
    busqueda.setAttribute("aria-activedescendant", opcion.id);
    if (desplazar) {
      const arriba = opcion.offsetTop;
      const abajo = arriba + opcion.offsetHeight;
      const vistaAbajo = sugerencias.scrollTop + sugerencias.clientHeight;
      if (arriba < sugerencias.scrollTop) sugerencias.scrollTop = arriba;
      if (abajo > vistaAbajo) sugerencias.scrollTop = abajo - sugerencias.clientHeight;
    }
  } else {
    busqueda.removeAttribute("aria-activedescendant");
  }
}

function renderizarSugerencias() {
  marcarSugerencia(-1);
  const fragmento = document.createDocumentFragment();
  for (const [indice, municipio] of visibles.entries()) {
    const fila = document.createElement("li");
    fila.id = `municipio-${municipio.codigo_municipio}`;
    fila.className = "municipio-lista";
    fila.dataset.indice = indice;
    fila.setAttribute("role", "option");
    fila.setAttribute("aria-selected", "false");
    const texto = document.createElement("span");
    const nombre = document.createElement("strong");
    nombre.textContent = municipio.nombre;
    const descripcion = document.createElement("small");
    descripcion.textContent = etiqueta(municipio);
    texto.append(nombre, descripcion);
    fila.append(punto(grupo(municipio)), texto);
    fragmento.append(fila);
  }
  lista.replaceChildren(fragmento);
  lista.hidden = visibles.length === 0;
  obtener("sugerencias-vacias").hidden = visibles.length > 0;
  sugerencias.scrollTop = 0;
}

function abrirSugerencias() {
  if (!sugerencias.hidden) return;
  renderizarSugerencias();
  sugerencias.hidden = false;
  busqueda.setAttribute("aria-expanded", "true");
}

function cerrarSugerencias() {
  if (sugerencias.hidden) return;
  marcarSugerencia(-1);
  sugerencias.hidden = true;
  busqueda.setAttribute("aria-expanded", "false");
}

function elegirSugerencia(indice) {
  seleccionar(visibles[indice]);
  cerrarSugerencias();
  mostrarFichaEnMovil();
}

function conectarBuscador() {
  busqueda.addEventListener("focus", abrirSugerencias);
  busqueda.addEventListener("click", abrirSugerencias);
  busqueda.addEventListener("input", () => {
    aplicarFiltros();
    abrirSugerencias();
  });
  busqueda.addEventListener("keydown", (evento) => {
    if (evento.isComposing) return;
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      abrirSugerencias();
      if (visibles.length === 0) return;
      const ultimo = visibles.length - 1;
      const proximo = evento.key === "ArrowDown"
        ? Math.min(ultimo, indiceActivo + 1)
        : indiceActivo <= 0 ? ultimo : indiceActivo - 1;
      marcarSugerencia(proximo, true);
    } else if (evento.key === "Enter" && !sugerencias.hidden) {
      evento.preventDefault();
      if (indiceActivo >= 0 || visibles.length === 1) {
        elegirSugerencia(Math.max(0, indiceActivo));
      }
    } else if (evento.key === "Escape" && !sugerencias.hidden) {
      evento.preventDefault();
      cerrarSugerencias();
    } else if (evento.key === "Tab") {
      cerrarSugerencias();
    }
  });
  lista.addEventListener("mousedown", (evento) => {
    if (evento.target.closest("[role=option]")) evento.preventDefault();
  });
  lista.addEventListener("click", (evento) => {
    const opcion = evento.target.closest("[role=option]");
    if (opcion) elegirSugerencia(Number(opcion.dataset.indice));
  });
  const campoBusqueda = busqueda.closest(".campo-busqueda");
  for (const evento of ["pointerdown", "focusin"]) {
    document.addEventListener(evento, ({ target }) => {
      if (!campoBusqueda.contains(target)) cerrarSugerencias();
    });
  }
}

function mostrarFichaEnMovil() {
  if (pantallaEstrecha.matches) {
    const titulo = obtener("ficha-titulo");
    titulo.focus({ preventScroll: true });
    titulo.scrollIntoView({ block: "start" });
  }
}

function aplicarFiltros() {
  const consulta = normalizar(busqueda.value);
  visibles = datos.municipios.filter((municipio) =>
    (!consulta || municipio.indice.includes(consulta))
    && (!provincia.value || municipio.codigo_provincia === provincia.value)
    && (!perfil.value || grupo(municipio) === perfil.value));
  const codigos = new Set(visibles.map((municipio) => municipio.codigo_municipio));
  for (const [codigo, recinto] of recintos) {
    recinto.classList.toggle("atenuado", !codigos.has(codigo));
  }
  if (seleccion && !codigos.has(seleccion.codigo_municipio)) seleccionar(null);
  tooltip.hidden = true;
  const total = visibles.length;
  obtener("recuento").textContent = `${formato.format(total)} ${total === 1 ? "municipio" : "municipios"}`;
  const mensaje = obtener("mapa-mensaje");
  mensaje.hidden = total > 0;
  mensaje.textContent = "Sin coincidencias. Prueba a cambiar la búsqueda o los filtros.";
  obtener("restablecer").disabled = !busqueda.value && !provincia.value && !perfil.value;
  if (!sugerencias.hidden) renderizarSugerencias();
}

function conectarControles() {
  const provincias = Object.entries(datos.provincias).sort((a, b) => ordenar.compare(a[1], b[1]));
  for (const [codigo, nombre] of provincias) provincia.add(new Option(nombre, codigo));
  obtener("leyenda").closest("details").open = !pantallaEstrecha.matches;
  for (const [codigo, nombre] of [...Object.entries(datos.perfiles), [SIN_PERFIL, "Sin perfil"]]) {
    perfil.add(new Option(nombre, codigo));
    const fila = document.createElement("li");
    fila.append(punto(codigo), document.createTextNode(nombre));
    obtener("leyenda").append(fila);
  }
  for (const control of [busqueda, provincia, perfil]) control.disabled = false;
  formulario.addEventListener("submit", (evento) => evento.preventDefault());
  conectarBuscador();
  provincia.addEventListener("change", () => aplicarFiltros());
  perfil.addEventListener("change", () => aplicarFiltros());
  formulario.addEventListener("reset", (evento) => {
    evento.preventDefault();
    busqueda.value = provincia.value = perfil.value = "";
    aplicarFiltros();
    busqueda.focus();
    cerrarSugerencias();
  });
  obtener("filtrar-perfil").addEventListener("click", () => {
    if (!seleccion || seleccion.perfil === null) return;
    busqueda.value = provincia.value = "";
    perfil.value = seleccion.perfil;
    aplicarFiltros();
    busqueda.focus();
    abrirSugerencias();
  });
  obtener("cerrar-ficha").addEventListener("click", () => {
    seleccionar(null);
    busqueda.focus();
    cerrarSugerencias();
  });
  obtener("acercar").addEventListener("click", () => zoom(0.67));
  obtener("alejar").addEventListener("click", () => zoom(1 / 0.67));
  obtener("centrar").disabled = false;
  obtener("centrar").addEventListener("click", () => establecerVista(vistaRegional));

  mapa.addEventListener("pointerdown", (evento) => {
    if (!evento.isPrimary || evento.button !== 0) return;
    evitarClick = false;
    arrastre = { id: evento.pointerId, x: evento.clientX, y: evento.clientY, origen: vista, movido: false };
  });
  mapa.addEventListener("pointermove", (evento) => {
    if (arrastre?.id !== evento.pointerId) return;
    const dx = evento.clientX - arrastre.x;
    const dy = evento.clientY - arrastre.y;
    if (!arrastre.movido && Math.hypot(dx, dy) < 5) return;
    if (!arrastre.movido) {
      mapa.setPointerCapture(evento.pointerId);
      arrastre.movido = true;
      mapa.classList.add("arrastrando");
    }
    const escala = vista.ancho / mapa.clientWidth;
    establecerVista({ ...arrastre.origen, x: arrastre.origen.x - dx * escala, y: arrastre.origen.y - dy * escala });
  });
  function terminarArrastre(evento) {
    if (arrastre?.id !== evento.pointerId) return;
    evitarClick = arrastre.movido;
    arrastre = null;
    mapa.classList.remove("arrastrando");
  }
  window.addEventListener("pointerup", terminarArrastre);
  window.addEventListener("pointercancel", terminarArrastre);
}

function mostrarErrorDeCarga(estado, detalle) {
  obtener("recuento").textContent = estado;
  const mensaje = obtener("mapa-mensaje");
  mensaje.textContent = detalle;
  mensaje.hidden = false;
}

async function iniciar() {
  try {
    const respuesta = await fetch("datos/municipios.json");
    if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
    datos = await respuesta.json();
    for (const municipio of datos.municipios) {
      municipio.nombre = nombreMunicipio(municipio.nombre_municipio);
      municipio.indice = normalizar(`${municipio.nombre_municipio} ${municipio.nombre} ${municipio.codigo_municipio}`);
    }
    datos.municipios.sort((a, b) => ordenar.compare(a.nombre, b.nombre));
    construirMapa();
    conectarControles();
    aplicarFiltros();
  } catch (error) {
    console.error(error);
    mostrarErrorDeCarga(
      "Datos no disponibles",
      "No se han podido cargar los municipios. Genera los datos del visor y vuelve a cargar la página.",
    );
  }
}

function conectarTema() {
  const control = obtener("tema");
  const clave = "recarga-cv:tema";

  function mostrarTema(tema) {
    document.documentElement.dataset.tema = tema;
    control.setAttribute("aria-pressed", String(tema === "oscuro"));
  }

  try {
    mostrarTema(localStorage.getItem(clave) === "oscuro" ? "oscuro" : "claro");
  } catch {
    mostrarTema("claro");
  }

  control.addEventListener("click", () => {
    const tema = document.documentElement.dataset.tema === "oscuro" ? "claro" : "oscuro";
    mostrarTema(tema);
    try {
      localStorage.setItem(clave, tema);
    } catch {
      // La elección sigue activa durante la visita si no hay almacenamiento.
    }
  });
}

if (sugerencias && obtener("tema")) {
  conectarTema();
  iniciar();
} else {
  mostrarErrorDeCarga(
    "Versión de la página desactualizada",
    "Pulsa Ctrl+F5 para cargar juntos la página y sus archivos.",
  );
}
