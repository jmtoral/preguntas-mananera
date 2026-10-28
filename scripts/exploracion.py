"""Arma la página de exploración «Quién pregunta y cada cuándo» con un solo corte.

Antes cada sección salía de un generador distinto, escrito en el scratchpad de
una sesión y perdido con él; la página publicada mezclaba cortes (31 de agosto
y 5 de octubre) y hasta grafías del mismo periodista. Aquí todas las cifras
salen de los mismos hilos canonizados, hasta la misma fecha.

    python scripts/exploracion.py --hasta 2026-09-30

Escribe `data/outputs/quien_pregunta.html`. La plantilla (CSS y scripts) es
`assets/exploracion_plantilla.html`, con los marcadores `{{CUERPO}}`,
`{{TEMAS_D}}`, `{{NM}}` y `{{RANGO_MESES}}`.

No usa ningún modelo ni gasta API: categoría y asunto ya están clasificados, y
`postura` NO entra (reprobó la compuerta; ver CLAUDE.md).
"""

from __future__ import annotations

import argparse
import collections
import csv
import html
import json
import re
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from buscar import _leer_jsonl, cargar_anexos, intercambios, plano  # noqa: E402
from consolidar_asuntos import SIN_ASUNTO, es_meta  # noqa: E402
from revisar import PROMESA, RANGO, hallazgos  # noqa: E402
from estenograficas import canonizar  # noqa: E402
from estenograficas.config import paths  # noqa: E402

MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]

e = html.escape


def n_(x: int) -> str:
    return f"{x:,}"


def pct(a: float, b: float, d: int = 1) -> str:
    return f"{100 * a / b:.{d}f}%" if b else "—"


def fecha_larga(f: str) -> str:
    a, m, d = f.split("-")
    return f"{int(d)} de {MES_LARGO[int(m) - 1]} de {a}"


def plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def recorte(t: str, n: int = 300) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def palabras(t: str) -> int:
    return len(t.split())


def es_ella(quien: str) -> bool:
    return "sheinbaum" in plano(quien or "")


# ------------------------------------------------------------------- datos

def cargar(corte: str) -> dict:
    p = paths()
    hilos = [h for h in _leer_jsonl(p.hilos) if h["conferencia_id"] <= corte]
    canonizar.aplicar(hilos, p.root / "config")
    por_hilo = {(h["conferencia_id"], h["hilo"]): h for h in hilos}

    temas, _postura, _urls = cargar_anexos()
    tax = json.loads((p.interim / "taxonomia_temas_candidata.json").read_text(encoding="utf-8"))
    nombre_cat = {c["clave"]: c["nombre"] for c in tax["categorias"]}

    ics = []
    for ic in intercambios():
        conf = ic["conferencia_id"]
        if conf > corte:
            continue
        h = por_hilo[(conf, ic["hilo"])]
        tema = temas.get(f"{conf}-t{ic['orden']}", {})
        ella = [r for r, q in zip(ic["respuestas"], ic["quien_por_turno"]) if es_ella(q)]
        ics.append({
            "conf": conf, "mes": conf[:7],
            # `incierta` ya viene sin periodista desde `intercambios()`; se respeta.
            "per": h["periodista"] if ic["periodista"] else None,
            "medio": h["medio"] if ic["periodista"] else None,
            "preg": ic["pregunta"], "wq": palabras(ic["pregunta"]),
            "cat": tema.get("categoria") if tema.get("categoria") in nombre_cat else None,
            "asunto": tema.get("asunto"),
            "ella": ella, "wa": sum(palabras(r) for r in ella),
        })

    confs = sorted(c["conferencia_id"] for c in _leer_jsonl(p.interim / "conferencias.jsonl")
                   if c["conferencia_id"] <= corte)
    meses = sorted({c[:7] for c in confs})
    mapa = json.loads((p.interim / "mapa_consolidacion.json").read_text(encoding="utf-8"))

    # Una ficha por periodista. `medio` es su cabecera principal más frecuente.
    P: dict[str, dict] = {}
    for h in hilos:
        d = P.setdefault(h["periodista"], {"interv": 0, "preg": 0, "meses": collections.Counter(),
                                           "fechas": set(), "medios": collections.Counter()})
        d["interv"] += 1
        d["meses"][h["conferencia_id"][:7]] += 1
        d["fechas"].add(h["conferencia_id"])
        if h.get("medio"):
            d["medios"][h["medio"]] += 1
    for ic in ics:
        if ic["per"]:
            P[ic["per"]]["preg"] += 1
    for d in P.values():
        d["medio"] = d["medios"].most_common(1)[0][0] if d["medios"] else ""

    return {"corte": corte, "hilos": hilos, "ics": ics, "confs": confs, "meses": meses,
            "P": P, "nombre_cat": nombre_cat, "mapa": mapa}


def etiqueta_mes(m: str, largo: bool = False) -> str:
    a, mm = m.split("-")
    return f"{MES[int(mm) - 1]} {a if largo else a[2:]}"


def ranking(D) -> list[str]:
    return sorted(D["P"], key=lambda p: (-D["P"][p]["interv"], -D["P"][p]["preg"], p))


def qui(p: str, medio: str, cls: str = "qui") -> str:
    return f'<div class="{cls}"><b>{e(p)}</b><span>{e(medio)}</span></div>'


# --------------------------------------------------- 0 · mapa de calor

def s_calor(D) -> str:
    P, meses, top = D["P"], D["meses"], ranking(D)[:100]
    mx = P[top[0]]["interv"]
    mxc = max(P[p]["meses"][m] for p in top for m in meses)
    filas = []
    for p in top:
        d = P[p]
        celdas = "".join(
            f'<div class="c p{min(5, max(1, n - 1)) if n else 0}" tabindex="0" '
            f'data-t="{e(p)} · {etiqueta_mes(m, True)} · {n} intervenci{"ón" if n == 1 else "ones"}"></div>'
            for m in meses for n in [d["meses"][m]])
        act = sum(1 for m in meses if d["meses"][m])
        filas.append(f'<div class="fila">{qui(p, d["medio"])}<div class="rej">{celdas}</div>'
                     f'<div class="tot"><div class="bar" style="width:{round(100 * d["interv"] / mx)}%"></div>'
                     f'<span>{d["interv"]}</span></div><div class="act">{act}<span>/{len(meses)}</span></div></div>')
    ejes = "".join(
        f'<div class="m hito">ene<b>{m[:4]}</b></div>' if m.endswith("-01")
        else '<div class="m hito">jul</div>' if m.endswith("-07") else '<div class="m"></div>'
        for m in meses)
    con_prensa = len({h["conferencia_id"] for h in D["hilos"]})
    return f"""<p class="et">Conferencias matutinas · de la del {fecha_larga(D['confs'][0])} a la del {fecha_larga(D['confs'][-1])} · {n_(len(D['confs']))} en total</p>
<h1>Quién pregunta y cada cuándo</h1>
<p class="sub">Los 100 periodistas que más veces han recibido la palabra en las {n_(con_prensa)}
conferencias donde al menos un periodista dijo su nombre (de {n_(len(D['confs']))} en total). Cada celda es un mes: mientras más oscura, <b>más veces le dieron la palabra</b>
ese mes. Una <b>intervención</b> es cada vez que un periodista toma el micrófono y hace su
serie de preguntas.</p>

<div class="panel"><div class="rejilla">
<div class="cab"><div>Periodista</div><div>Intervenciones por mes</div>
<div>Total</div><div>Meses</div></div>
{''.join(filas)}
<div class="ejes"><div></div><div>{ejes}</div><div></div><div></div></div>
<div class="pie">
 <div class="esc">Intervenciones en el mes:<i class="p0"></i><i class="p1"></i><i class="p2"></i>
 <i class="p3"></i><i class="p4"></i><i class="p5"></i>
 <span style="margin-left:4px">0 → {mxc}</span></div>
 <div>La barra de la derecha es el total en los {len(meses)} meses.</div>
</div>
</div></div>
"""


# ------------------------------------------------ 1 · concentración

def s_concentracion(D) -> str:
    P, r = D["P"], ranking(D)
    tot = sum(P[p]["interv"] for p in r)
    mx = P[r[0]]["interv"]
    acum, mitad = 0, None
    for i, p in enumerate(r):
        acum += P[p]["interv"]
        if mitad is None and acum >= tot / 2:
            mitad = i + 1
    top10 = sum(P[p]["interv"] for p in r[:10])

    filas, acum = [], 0
    for p in r[:10]:
        d = P[p]
        acum += d["interv"]
        filas.append(f'<div class="cf">{qui(p, d["medio"], "cq")}<div class="cb"><i style="width:{100 * d["interv"] / mx:.1f}%"></i></div>'
                     f'<div class="cn cbig">{pct(d["interv"], tot)}</div><div class="cn">{d["interv"]}</div>'
                     f'<div class="cn">{d["preg"]}</div><div class="cn cac">{pct(acum, tot)}</div></div>')
    c50 = []
    for i, p in enumerate(r[:50], 1):
        d = P[p]
        c50.append(f'<div class="c5"><div class="c5n">{i}</div>{qui(p, d["medio"], "cq")}'
                   f'<div class="cb"><i style="width:{100 * d["interv"] / mx:.1f}%"></i></div>'
                   f'<div class="cn cbig">{d["interv"]}</div><div class="cn">{d["preg"]}</div>'
                   f'<div class="cn">{d["preg"] / d["interv"]:.1f}</div></div>')
    med50 = statistics.median(P[p]["interv"] for p in r[:50])
    resto = len(r) - 100
    tramos = [("los 10 primeros", r[:10]), ("del 11 al 50", r[10:50]), ("del 51 al 100", r[50:100]),
              (f"los otros {resto}", r[100:])]
    tr = [(nom, sum(P[p]["interv"] for p in ps)) for nom, ps in tramos]
    conc = "".join(f'<span class="tr t{i}" style="width:{100 * v / tot:.2f}%" title="{nom}: {v} intervenciones, {pct(v, tot)}"></span>'
                   for i, (nom, v) in enumerate(tr))
    leg = "".join(f'<span><s class="t{i}"></s>{nom} · <b>{pct(v, tot)}</b></span>' for i, (nom, v) in enumerate(tr))
    return f"""<h2>Cuánto del micrófono se llevan diez personas</h2>
<p class="nota">De las <strong>{n_(tot)} intervenciones</strong> repartidas en
{n_(len(r))} periodistas identificados, los diez primeros de la gráfica de arriba
concentran esto:</p>

<div class="hero">
 <div><b>{pct(top10, tot)}</b><span>de todas las intervenciones se las llevan diez personas</span></div>
 <div><b>{pct(10, len(r))}</b><span>es lo que esas diez representan del total de periodistas</span></div>
 <div><b>{mitad}</b><span>periodistas bastan para la mitad del micrófono</span></div>
</div>

<div class="panel"><div class="cgrid">
<div class="ccab"><div>Periodista</div><div>% de las intervenciones</div><div>%</div>
<div>Interv.</div><div>Preg.</div><div>Acum.</div></div>
{''.join(filas)}
</div></div>

<h3 class="wsub">Los 50 primeros, en crudo</h3>
<p class="nota">El número de veces que cada uno tomó el micrófono, sin normalizar. La caída
es la forma de la conferencia: de {P[r[0]]['interv']} intervenciones a {P[r[49]]['interv']} en cincuenta
puestos, con mediana de {med50:g}.</p>

<div class="panel"><div class="cgrid5">
<div class="c5cab"><div>#</div><div>Periodista</div><div>Intervenciones</div>
<div>Interv.</div><div>Preg.</div><div>Preg/int</div></div>
{''.join(c50)}
</div></div>

<h3 class="wsub">Cómo se reparte el total</h3>
<div class="panel">
<div class="conc">{conc}</div>
<div class="cleg">{leg}</div>
<p class="wleg" style="margin-top:12px">Las {n_(tot)} intervenciones repartidas por
tramos de frecuencia. La cola de {resto} periodistas —el {pct(resto, len(r), 0)} de las
personas— se reparte el {pct(tr[3][1], tot)}.</p></div>

<div class="aviso"><p><b>Cómo leer esta concentración.</b> Que diez personas tengan una quinta
parte del micrófono no prueba favoritismo por sí solo: los reporteros de fuente asisten a diario y
los demás van cuando les toca el tema, así que alguna concentración es esperable en cualquier
conferencia. Lo que sí es medible y está aquí es <b>cuánta</b>, y que la presidenta concede los
turnos a mano y en voz alta. Para el otro lado del argumento hace falta saber quién estaba en el
salón y no recibió la palabra, y eso la versión estenográfica no lo registra.</p></div>
"""


# ---------------------------------------------------- 2 · treemap

def squarify(vals: list[float], x: float, y: float, w: float, h: float) -> list[tuple]:
    """Treemap «squarified» (Bruls et al.): `vals` en orden descendente, suman w·h."""
    out, i = [], 0
    while i < len(vals):
        corto = min(w, h)

        def peor(fila):
            s = sum(fila)
            return max(max(corto * corto * v / (s * s), s * s / (corto * corto * v)) for v in fila)

        fila, j = [vals[i]], i + 1
        while j < len(vals) and peor(fila + [vals[j]]) <= peor(fila):
            fila.append(vals[j])
            j += 1
        s = sum(fila)
        if w >= h:
            cw, yy = s / h, y
            for v in fila:
                out.append((x, yy, cw, v / cw))
                yy += v / cw
            x, w = x + cw, w - cw
        else:
            rh, xx = s / w, x
            for v in fila:
                out.append((xx, y, v / rh, rh))
                xx += v / rh
            y, h = y + rh, h - rh
        i = j
    return out


def s_treemap(D) -> str:
    cuenta, quien = collections.Counter(), collections.defaultdict(collections.Counter)
    for h in D["hilos"]:
        for m in h["medios"]:
            cuenta[m] += 1
            quien[m][h["periodista"]] += 1
    orden = sorted(cuenta, key=lambda m: (-cuenta[m], m))
    tot, mx = sum(cuenta.values()), cuenta[orden[0]]
    W, H = 150.0, 100.0
    rects = squarify([cuenta[m] * W * H / tot for m in orden], 0, 0, W, H)
    cajas = []
    for i, (m, (x, y, w, h)) in enumerate(zip(orden, rects)):
        n, f = cuenta[m], cuenta[m] / mx
        cls = 5 if f >= .67 else 4 if f >= .40 else 3 if f >= .19 else 2 if f >= .06 else 1
        wp, hp = 100 * w / W, 100 * h / H
        lab = (f"<b>{e(m)}</b><i>{n} turnos</i>" if i < 10 else f"<b>{e(m)}</b><i>{n}</i>" if i < 50
               else f"<b>{e(m)}</b>" if wp >= 5 and hp >= 4.4 else "")
        k = len(quien[m])
        t = (f"{m} · {plural(n, 'intervención', 'intervenciones')} · {plural(k, 'periodista', 'periodistas')}, "
             f"sobre todo {quien[m].most_common(1)[0][0]}")
        cajas.append(f'<div class="tm p{cls}" style="left:{100 * x / W:.3f}%;top:{100 * y / H:.3f}%;'
                     f'width:{wp:.3f}%;height:{hp:.3f}%" tabindex="0" data-t="{e(t)}">{lab}</div>')
    acum, mitad = 0, 0
    for i, m in enumerate(orden):
        acum += cuenta[m]
        if acum >= tot / 2:
            mitad = i + 1
            break
    grupos = [("10 o más veces", lambda n: n >= 10), ("de 3 a 9 veces", lambda n: 3 <= n <= 9),
              ("dos veces", lambda n: n == 2), ("una sola vez", lambda n: n == 1)]
    cinta, leg, g = [], [], []
    for i, (nom, f) in enumerate(grupos, 1):
        ms = [m for m in orden if f(cuenta[m])]
        v = sum(cuenta[m] for m in ms)
        g.append((len(ms), v))
        span = f"<span>{pct(v, tot, 0)}</span>" if v / tot >= .05 else ""
        cinta.append(f'<div class="tmt t{i}" style="width:{100 * v / tot:.3f}%" tabindex="0" '
                     f'data-t="{len(ms)} medios que aparecen {nom} · {v} turnos · {pct(v, tot, 0)} del total">{span}</div>')
        leg.append(f'<span class="tmk"><i class="t{i}"></i><b>{len(ms)}</b>&nbsp;medios, {nom}</span>')
    nh = len(D["hilos"])
    return f"""<h2>Qué medios reciben la palabra</h2>

<p class="wint">Cada cuadro es un medio y su área es el número de veces que alguien de ese
medio tomó la palabra. Están <b>los {n_(len(orden))}</b>, no una selección: los {n_(tot)} turnos
repartidos a lo largo de {n_(nh)} tandas de pregunta. Los <b>{mitad} primeros</b> se
llevan la mitad; todo lo demás es el campo de astillas de la derecha.</p>

<div class="panel">
<div class="tmw">{''.join(cajas)}</div>
<div class="tmleg"><span class="tmk"><i class="p1"></i>pocos turnos</span><span class="tmk"><i class="p3"></i></span><span class="tmk"><i class="p5"></i>muchos</span></div>
<p class="wleg" style="margin-top:12px">Pasa el cursor o tabula por cualquier cuadro, por
chico que sea, para ver el medio, cuántos turnos tuvo y quién lo representa. Cuando alguien
nombra varias cabeceras en su presentación, cada una cuenta su turno: por eso hay más turnos que tandas.</p>

<h3 class="wsub" style="margin-top:26px">Cuántos medios van una sola vez</h3>
<div class="tmcinta">{''.join(cinta)}</div>
<div class="tmleg">{''.join(leg)}</div>
<p class="wleg" style="margin-top:10px">La misma barra reparte los {n_(tot)} turnos según qué
tan seguido aparece el medio. <b>{g[3][0]} de los {n_(len(orden))} medios aparecen una sola vez</b> en
{n_(nh)} tandas, y entre todos ellos se llevan el {pct(g[3][1], tot, 0)} de los turnos.</p>
</div>
"""


# ------------------------------------------- 3 · de qué pregunta cada quien

def legible(D, asunto) -> str | None:
    if not asunto or es_meta(asunto):
        return None
    c = D["mapa"].get(asunto, asunto)
    return None if c == SIN_ASUNTO else c


def s_temas(D) -> str:
    ics, nc = D["ics"], D["nombre_cat"]
    clas = [ic for ic in ics if ic["cat"]]
    glob = collections.Counter(ic["cat"] for ic in clas)
    mxg = glob.most_common(1)[0][1]
    gl = "".join(f'<div class="cat"><span class="cn">{e(nc[k])}</span><span class="cb"><i style="width:{round(100 * v / mxg)}%"></i></span>'
                 f'<span class="cp">{pct(v, len(clas))}</span></div>' for k, v in glob.most_common())

    por = collections.defaultdict(list)
    for ic in clas:
        if ic["per"]:
            por[ic["per"]].append(ic)
    top = sorted(por, key=lambda p: (-len(por[p]), p))[:100]
    tarjetas = []
    for p in top:
        L = por[p]
        cats = collections.Counter(ic["cat"] for ic in L)
        cs = []
        for k, v in cats.most_common(5):
            ej = max((ic for ic in L if ic["cat"] == k), key=lambda ic: len(ic["preg"]))
            cs.append(f'<div class="cat tq" tabindex="0" data-q="{e(recorte(ej["preg"]))}" data-f="{ej["conf"]}">'
                      f'<span class="cn">{e(nc[k])}</span><span class="cb"><i style="width:{round(100 * v / len(L))}%"></i></span>'
                      f'<span class="cp">{round(100 * v / len(L))}%</span></div>')
        asu = collections.defaultdict(list)
        sin = 0
        for ic in L:
            a = legible(D, ic["asunto"])
            if a:
                asu[a].append(ic)
            else:
                sin += 1
        rep = sorted((a for a in asu if len(asu[a]) > 1), key=lambda a: (-len(asu[a]), min(i["conf"] for i in asu[a]), a))
        lis = []
        for a in rep[:10]:
            fs = sorted({i["conf"] for i in asu[a]})
            ej = max(asu[a], key=lambda ic: len(ic["preg"]))
            fe = (f'<span class="fe fx">{fs[0]} → {fs[-1]}</span>' if len(fs) > 1 else f'<span class="fe">{fs[0]}</span>')
            lis.append(f'<li class="tq" tabindex="0" data-q="{e(recorte(ej["preg"]))}" data-f="{ej["conf"]}">'
                       f'<b>{len(asu[a])}×</b> {e(a)} {fe}</li>')
        if not lis:
            lis.append('<li class="vacio">Ningún asunto se repite.</li>')
        unos = sum(1 for a in asu if len(asu[a]) == 1)
        cola = [f"{n_(unos)} asuntos más, de una sola aparición"]
        if len(rep) > 10:
            cola.append(f"{len(rep) - 10} más que se repiten")
        if sin:
            cola.append(f"{sin} sin asunto legible")
        medio = D["P"][p]["medio"]
        tarjetas.append(f"""<article class="tj">
<header><b>{e(p)}</b><span>{e(medio)}</span>
<em>{n_(len(L))} preguntas · {len({ic['conf'] for ic in L})} conferencias · {n_(len(asu))} asuntos</em></header>
<div class="cats">{''.join(cs)}</div>
<ul class="asu">{''.join(lis)}</ul>
<p class="cola">{' · '.join(cola)}</p>
</article>""")

    crudos = {ic["asunto"] for ic in clas if ic["asunto"] and not es_meta(ic["asunto"])}
    grupos = collections.defaultdict(set)
    for a in crudos:
        grupos[D["mapa"].get(a, a)].add(a)
    funden = [g for g in grupos.values() if len(g) > 1]
    return f"""<h2>De qué pregunta cada quien</h2>
<p class="nota">Cada pregunta se clasificó en dos niveles: una de 18 <strong>categorías</strong>
cerradas, para poder tabular, y un <strong>asunto</strong> abierto — el caso concreto, con nombres —
para poder seguir una historia. Va clasificado <strong>{n_(len(clas))} de {n_(len(ics))}</strong> ({pct(len(clas), len(ics), 0)}) de las preguntas
útiles del corpus.</p>

<div class="panel"><div class="globcat">{gl}</div>
<p class="wleg">Las 18 categorías sobre las {n_(len(clas))} preguntas clasificadas.</p></div>

<p class="nota">Abajo, los 100 periodistas con más preguntas clasificadas: sus cinco
categorías principales y los asuntos a los que vuelven. Las fechas en azul marcan los asuntos que
cruzan de una conferencia a otra. <strong>Pasa el cursor sobre cualquier categoría o asunto</strong> para leer una pregunta real de esa persona sobre ese tema.</p>

<div class="tjs">{''.join(tarjetas)}</div>

<div class="aviso"><p><b>Los asuntos ya están consolidados.</b> El modelo produjo
{n_(len(crudos))} asuntos distintos, muchos de ellos el mismo caso con otras palabras —<i>Deuda Pemex pago
proveedores</i> y <i>Adeudos Pemex proveedores fin de año</i>—. Juntarlos deja
{n_(len(grupos))} asuntos canónicos; <b>{n_(len(funden))} grupos</b> reúnen más de una variante, el mayor {max(map(len, funden))}.
Cada variante tiene que compartir con el nombre que encabeza su grupo al menos el 60% de su vocabulario;
el asunto crudo del modelo se conserva intacto y el mapa vive aparte, así que la consolidación se
puede rehacer con otro umbral sin volver a clasificar nada.</p></div>
"""


# ------------------------------------------------- 4 · temas mes a mes

def s_temas_mes(D) -> tuple[str, str]:
    meses, nc = D["meses"], D["nombre_cat"]
    clas = [ic for ic in D["ics"] if ic["cat"]]
    serie = {k: [0] * len(meses) for k in nc}
    for ic in clas:
        serie[ic["cat"]][meses.index(ic["mes"])] += 1
    orden = sorted(nc, key=lambda k: -sum(serie[k]))
    cpm = collections.Counter(c[:7] for c in D["confs"])
    confs = [cpm[m] for m in meses]
    otras = orden[8:]
    datos = {
        "meses": [etiqueta_mes(m, True) for m in meses], "corto": [etiqueta_mes(m) for m in meses],
        "confs": confs,
        "cats": [{"k": k, "n": nc[k], "t": sum(serie[k]), "s": serie[k]} for k in orden[:8]],
        "otras": {"n": f"Otros {len(otras)} temas", "t": sum(sum(serie[k]) for k in otras),
                  "s": [sum(serie[k][i] for k in otras) for i in range(len(meses))]},
    }
    cab = "".join(f'<th class="n">{etiqueta_mes(m)}</th>' for m in meses)
    filas = "".join(f'<tr><td>{e(nc[k])}</td>' + "".join(f'<td class="n">{v}</td>' for v in serie[k])
                    + f'<td class="n">{n_(sum(serie[k]))}</td></tr>' for k in orden)
    completos = [c for c in confs if c >= 15]
    med = nc["medios_de_comunicacion"]
    cuerpo = f"""<h2 id="temas-tiempo">De qué se pregunta, mes a mes</h2>
<p class="nota">Cuántas preguntas de la prensa se hicieron cada mes en cada tema, sobre las
<strong>{n_(len(clas))}</strong> preguntas clasificadas. Cada punto es un mes completo de conferencias.
Elige los temas que quieras comparar; los ocho más frecuentes tienen su propio color y los otros
{len(otras)} van juntos en gris.</p>
<div class="tmg" id="tmg">
 <div class="tmg-chips" id="tmg-chips" role="group" aria-label="Temas"></div>
 <div class="tmg-wrap" id="tmg-wrap"><div class="tmg-tip" id="tmg-tip"></div></div>
 <div class="aviso" id="tmg-aviso" hidden><p><b>Ojo con «{e(med)}».</b> Además de preguntas sobre medios, recoge turnos sin contenido (agradecimientos, preguntas incompletas, «turno de preguntas») en una cantidad que cambió entre corridas de clasificación: 72, 64 y 37 en junio, julio y agosto de 2026, y solo 3 en septiembre. La caída de esa línea en septiembre viene de cómo se clasificó, no de lo que se preguntó.</p></div>
</div>
<p class="rvsuma">Número de preguntas por mes; no están normalizadas por el número de conferencias del mes
(entre {min(completos)} y {max(completos)}).</p>
<details class="tmg-tabla"><summary>Ver los números de los 18 temas</summary>
<div class="tabla-env"><table><thead><tr><th>Tema</th>{cab}<th class="n">Total</th></tr></thead><tbody>
{filas}
</tbody></table></div></details>
"""
    return cuerpo, json.dumps(datos, ensure_ascii=False)


# --------------------------------------------------- 5 · dendrograma

# Palabras de función y fórmulas de cortesía. Sin ellas, todos se parecen a todos.
VACIAS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun bien cada como con contra cual
cuales cuando de del desde donde dos el ella ellas ello ellos en entre era eran es esa esas ese eso
esos esta estaba estado estan estar estas este esto estos fue fueron ha habia han hasta hay la las le
les lo los mas me mi mis muy nada ni no nos nosotros o otra otras otro otros para pero por porque pues
que quien quienes se sea ser si sido sin sobre son su sus tambien tan tanto te tiene tienen todo todos
tu un una unas uno unos usted ustedes y ya yo hace hacer puede pueden esta estamos tenemos sera seria
ahi alla entonces bueno digo decir dice dijo cosa cosas forma parte caso vez veces tema temas manera
presidenta presidente buenos buenas dias tardes gracias muchas muchisimas favor permite permitio senora
pregunta preguntas preguntar preguntarle quisiera queria quiero saber gustaria comentar comentarle
nuestro nuestra nuestros nuestras ademas mismo misma mismos solo sino segun luego asimismo e u
este esa aquel aquella hoy ayer ahora siempre nunca mientras donde aunque tras mediante cual
""".split())


def tokens(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-zñ]+", plano(t)) if len(w) > 2 and w not in VACIAS]


def s_dendrograma(D) -> str:
    P = D["P"]
    por = collections.defaultdict(list)
    for ic in D["ics"]:
        if ic["per"]:
            por[ic["per"]].append(ic["preg"])
    top = sorted(por, key=lambda p: (-len(por[p]), p))[:20]
    # Los periodistas se autopresentan dentro de sus preguntas: sin quitar los
    # nombres de todos (personas y medios), la distancia mediría quién se llama cómo.
    propios = set()
    for p, d in P.items():
        propios.update(tokens(p))
        for m in d["medios"]:
            propios.update(tokens(m))
    voc, frec = {}, {}
    for p in top:
        c = collections.Counter(w for t in por[p] for w in tokens(t) if w not in propios)
        frec[p] = c
        voc[p] = {w for w, _ in c.most_common(400)}
    n = len(top)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            a, b = voc[top[i]], voc[top[j]]
            M[i, j] = M[j, i] = 1 - len(a & b) / len(a | b)
    Z = linkage(squareform(M), "average")
    hojas = dendrogram(Z, no_plot=True)["leaves"]

    dmin, dmax = Z[:, 2].min() - .03, Z[:, 2].max() + .01
    X0, X1, Y0, Y1, XH = 200.0, 734.0, 20.0, 574.0, 754.0

    def X(d):
        return X0 + (dmax - d) / (dmax - dmin) * (X1 - X0)

    paso = (Y1 - Y0) / (n - 1)
    pos = {h: (XH, Y0 + k * paso) for k, h in enumerate(hojas)}
    miembros = {i: [top[i]] for i in range(n)}
    svg = []
    for k in range(6):
        d = dmin + .03 + k * (dmax - .01 - dmin - .03) / 5
        svg.append(f'<line class="dg" x1="{X(d):.1f}" y1="14" x2="{X(d):.1f}" y2="{Y1:.0f}"/>'
                   f'<text class="da" x="{X(d):.1f}" y="590" text-anchor="middle">{d:.2f}</text>')
    nodos = []
    for k, (a, b, d, _) in enumerate(Z):
        a, b = int(a), int(b)
        (xa, ya), (xb, yb), x = pos[a], pos[b], X(d)
        svg.append(f'<path class="dl" d="M{xa:.1f} {ya:.1f} H{x:.1f} V{yb:.1f} H{xb:.1f}"/>')
        pos[n + k] = (x, (ya + yb) / 2)
        miembros[n + k] = miembros[a] + miembros[b]
        nodos.append(f'<circle class="dp" cx="{x:.1f}" cy="{(ya + yb) / 2:.1f}" r="8"><title>{e(", ".join(miembros[a]))}\n—\n'
                     f'{e(", ".join(miembros[b]))}\n\ndistancia {d:.3f}</title></circle>')
    etq = []
    for k, h in enumerate(hojas):
        p, y = top[h], Y0 + k * paso
        etq.append(f'<text class="dn" x="190" y="{y - 1:.1f}" text-anchor="end">{e(p)}</text>'
                   f'<text class="dm" x="190" y="{y + 9.5:.1f}" text-anchor="end">{e(P[p]["medio"])} · {len(por[p])}</text>')

    iu = np.triu_indices(n, 1)
    k1, k2 = np.argmin(M[iu]), np.argmax(M[iu])
    c1, c2 = (top[iu[0][k1]], top[iu[1][k1]]), (top[iu[0][k2]], top[iu[1][k2]])

    def primeras(a, b, k=14):
        return ", ".join(f"<i>{w}</i>" for w in [w for w, _ in frec[a].most_common(400) if w not in voc[b]][:k])

    return f"""<h2>Quién se parece a quién por lo que dice</h2>
<p class="nota">Los 20 periodistas con más preguntas, agrupados por
<strong>las palabras que usan</strong>. Para cada uno se toman sus 400 palabras más
frecuentes y se mide la <strong>distancia de Jaccard</strong> entre esos vocabularios: 0 sería
usar exactamente las mismas palabras, 1 no compartir ninguna. Las ramas que se juntan a la derecha
son las más parecidas.</p>

<div class="aviso">
<p>
<b>Se quitaron sus propios nombres.</b> Los periodistas se autopresentan
dentro de sus preguntas, así que su nombre y el de su medio aparecían como vocabulario
distintivo. Sin filtrarlos, la distancia mediría quién se llama cómo en vez de de qué habla.
También se quitan las palabras de función —artículos, preposiciones, fórmulas de cortesía—.</p>
</div>

<div class="panel dend">
<svg viewBox="0 0 760 620" role="img"
 aria-label="Dendrograma de 20 periodistas según el vocabulario de sus preguntas">
{''.join(svg)}
{''.join(nodos)}
{''.join(etq)}
 <text class="da" x="467" y="612" text-anchor="middle" style="font-size:11px">
  ← más distinto    ·    distancia de Jaccard    ·    vocabulario más parecido →</text>
</svg>
<p class="wleg">Cada nodo muestra su distancia al pasar el cursor. Bajo cada nombre, su medio
principal y cuántas preguntas hizo.</p>
</div>

<div class="pal">
<b>El par más parecido: {e(c1[0])} y {e(c1[1])}</b> — distancia {M[iu][k1]:.3f}.
Comparten {len(voc[c1[0]] & voc[c1[1]])} de sus 400 palabras más usadas.</div>

<div class="pal">
<b>El par más distante: {e(c2[0])} y {e(c2[1])}</b> — distancia {M[iu][k2]:.3f}.
<p>Palabras de <b>{e(c2[0])}</b> que no están entre las de {e(c2[1])}:<br>
{primeras(*c2)}
</p>
<p>Y al revés, de <b>{e(c2[1])}</b>:<br>
{primeras(c2[1], c2[0])}
</p>
</div>

<div class="aviso">
<p>
<b>Qué mide y qué no.</b> Esto agrupa por vocabulario, y el vocabulario
refleja sobre todo <b>de qué se habla</b>. No mide postura — dos personas pueden usar
las mismas palabras para decir cosas opuestas. Y no incorpora ninguna etiqueta de afinidad: el
agrupamiento sale solo del texto. Tratarlo como pista de dónde mirar, no como evidencia de
alineamiento.</p>
</div>
"""


# --------------------------------------------------- 6 · palabras

def s_palabras(D) -> str:
    ics = D["ics"]
    wq_tot = sum(ic["wq"] for ic in ics)
    wa_tot = sum(ic["wa"] for ic in ics)
    S = collections.defaultdict(lambda: {"n": 0, "wq": 0, "wa": 0, "confs": set()})
    for ic in ics:
        if ic["ella"] and ic["per"]:
            s = S[ic["per"]]
            s["n"] += 1
            s["wq"] += ic["wq"]
            s["wa"] += ic["wa"]
            s["confs"].add(ic["conf"])
    top = sorted(S, key=lambda p: (-S[p]["n"], p))[:100]
    for p in top:
        s = S[p]
        s["q"], s["a"], s["r"] = s["wq"] / s["n"], s["wa"] / s["n"], s["wa"] / s["wq"]
    medio = {p: D["P"][p]["medio"] for p in top}

    # 1 · en bruto
    b = sorted(top, key=lambda p: -S[p]["wa"])
    mxa = S[b[0]]["wa"]
    bruto = "".join(
        f'<div class="bf">{qui(p, medio[p], "wq")}<div class="bt"><i style="width:{100 * S[p]["wa"] / mxa:.1f}%"></i></div>'
        f'<div class="wn wbig">{S[p]["wa"] / 1000:.1f}</div><div class="wn">{len(S[p]["confs"])}</div>'
        f'<div class="wn">{S[p]["n"]}</div><div class="wn">{round(S[p]["a"])}</div></div>' for p in b)
    w100 = sum(S[p]["wa"] for p in top)
    q100 = sum(S[p]["wq"] for p in top)

    # 2 · por turno
    tope = 40 * -(-max(max(S[p]["q"], S[p]["a"]) for p in top) // 40)
    turno = []
    for p in sorted(top, key=lambda p: -S[p]["r"]):
        s = S[p]
        lq, la = 100 * s["q"] / tope, 100 * s["a"] / tope
        turno.append(f'<div class="wf" data-r="{s["r"]:.4f}" data-q="{s["q"]:.1f}" data-a="{s["a"]:.1f}">{qui(p, medio[p], "wq")}'
                     f'<div class="wt"><span class="wl" style="left:{min(lq, la):.2f}%;width:{abs(la - lq):.2f}%"></span>'
                     f'<i class="dq" style="left:{lq:.2f}%" title="{round(s["q"])} palabras por pregunta"></i>'
                     f'<i class="da" style="left:{la:.2f}%" title="{round(s["a"])} palabras por respuesta"></i></div>'
                     f'<div class="wn">{round(s["q"])}</div><div class="wn">{round(s["a"])}</div><div class="wn wnr">{s["r"]:.2f}</div></div>')
    eje = "".join(f'<span style="left:{20 * k:.1f}%">{round(tope * k / 5)}</span>' for k in range(6))

    # totales
    topek = 20 * -(-max(max(S[p]["wq"], S[p]["wa"]) for p in top) / 1000 // 20)
    tot = []
    for p in b:
        s = S[p]
        lq, la = s["wq"] / 10 / topek, s["wa"] / 10 / topek
        tot.append(f'<div class="tf">{qui(p, medio[p], "wq")}<div class="wt"><span class="wl" style="left:{min(lq, la):.1f}%;width:{abs(la - lq):.1f}%"></span>'
                   f'<i class="dq" style="left:{lq:.1f}%" title="pregunta {n_(s["wq"])} palabras"></i>'
                   f'<i class="da" style="left:{la:.1f}%" title="ella le responde {n_(s["wa"])} palabras"></i></div>'
                   f'<div class="wn">{round(s["wq"] / 1000)}</div><div class="wn wbig">{round(s["wa"] / 1000)}</div><div class="wn wnr">{s["r"]:.2f}</div></div>')
    ejet = "".join(f'<span style="left:{20 * k:.1f}%">{round(topek * k / 5)}</span>' for k in range(6))

    q = np.array([S[p]["q"] for p in top])
    a = np.array([S[p]["a"] for p in top])
    r = np.array([S[p]["r"] for p in top])
    rq, ra = np.corrcoef(q, r)[0, 1], np.corrcoef(a, r)[0, 1]
    largo = max(top, key=lambda p: S[p]["q"])

    # 3 · dispersión
    xmin, xmax = 10 * (q.min() // 10), 10 * -(-q.max() // 10)
    ymax = float(np.ceil(r.max()))
    def SX(v): return 62 + (v - xmin) / (xmax - xmin) * 538
    def SY(v): return 348 - v / ymax * 322
    grid = "".join(f'<line class="gr" x1="{SX(v):.1f}" y1="26" x2="{SX(v):.1f}" y2="348"/><text class="ax" x="{SX(v):.1f}" y="366" text-anchor="middle">{v:.0f}</text>'
                   for v in np.linspace(xmin, xmax, 7))
    grid += "".join(f'<line class="gr" x1="62" y1="{SY(v):.1f}" x2="600" y2="{SY(v):.1f}"/><text class="ax" x="52" y="{SY(v) + 3.5:.1f}" text-anchor="end">{v:.1f}</text>'
                    for v in np.linspace(0, ymax, 7))
    m_, b_ = np.polyfit(q, r, 1)
    x2 = min(xmax, (0 - b_) / m_) if m_ < 0 else xmax
    orden_r = sorted(top, key=lambda p: -S[p]["r"])
    marcados = set(orden_r[:5] + orden_r[-5:])
    puntos = "".join(f'<circle class="{"pd" if p in marcados else ""}" cx="{SX(S[p]["q"]):.1f}" cy="{SY(S[p]["r"]):.1f}" r="{6 if p in marcados else 4.5}">'
                     f'<title>{e(p)} — pregunta {round(S[p]["q"])} palabras, ella responde {round(S[p]["a"])}, razón {S[p]["r"]:.2f}</title></circle>'
                     for p in top)
    # Etiquetas sin encimarse: cada una baja de 13 en 13 hasta quedar libre.
    puestas, nombres = [], []
    for p in sorted(marcados, key=lambda p: SY(S[p]["r"])):
        x, y = SX(S[p]["q"]), SY(S[p]["r"]) + 3.5
        izq = x < 480
        x0, x1 = (x + 10, x + 10 + 7 * len(p)) if izq else (x - 10 - 7 * len(p), x - 10)
        while any(a0 < x1 and x0 < a1 and abs(y - yy) < 13 for a0, a1, yy in puestas):
            y += 13
        puestas.append((x0, x1, y))
        nombres.append(f'<text class="pe" x="{x + 10 if izq else x - 10:.1f}" y="{y:.1f}" '
                       f'text-anchor="{"start" if izq else "end"}">{e(p)}</text>')
    nombres = "".join(nombres)

    por_a = sorted(top, key=lambda p: -S[p]["a"])
    largos = ", ".join(f"<b>{e(p)}</b> ({round(S[p]['a'])})" for p in por_a[:5])
    cortos = ", ".join(f"<b>{e(p)}</b> ({round(S[p]['a'])})" for p in por_a[::-1][:4])
    return f"""<h2>Cuánto contesta la presidenta</h2>
<p class="nota">La versión estenográfica permite contar algo que nadie tiene que clasificar:
cuántas palabras dice cada quien. En todo el corpus la prensa pregunta <strong>{wq_tot / 1e6:.2f} millones de
palabras</strong> y la presidenta responde <strong>{wa_tot / 1e6:.2f} millones</strong>. Aquí están los
100 periodistas a quienes ella les ha contestado más preguntas, primero en bruto y luego por pregunta.
Cuenta solo lo que dijo ella: si contestó Harfuch o Ebrard, esas palabras no entran.</p>

<h3 class="wsub">1 · En bruto: cuántas palabras le ha respondido a cada quien</h3>
<p class="nota">Suma de todo lo que la presidenta les ha contestado desde octubre de 2024, sin
dividir entre nada. Entre los 100 acumulan <strong>{w100 / 1e6:.2f} millones de palabras</strong>.</p>

<div class="panel"><div class="bgrid">
<div class="bcab"><div>Periodista</div><div>Palabras que ella le responde</div>
<div>Miles</div><div>Conf.</div><div>Preg.</div><div>Por resp.</div></div>
{bruto}
</div></div>

<div class="aviso"><p><b>Este primer número mide sobre todo cuántas veces les dieron la palabra.</b>
{e(b[0])} encabeza porque ella le contestó en {len(S[b[0]]['confs'])} conferencias, no necesariamente porque le
conteste más generosamente. Para separar las dos cosas hay que dividir entre preguntas, que es lo que sigue.</p></div>

<h3 class="wsub">2 · Por pregunta: lo que dice él o ella, y lo que ella devuelve</h3>
<p class="nota">Cada renglón tiene dos puntos sobre el mismo eje de palabras. El hueco entre ellos
es cuánto más larga es la respuesta de la presidenta. Se puede reordenar.</p>

<div class="wtabs" role="tablist">
 <button type="button" class="wtab" data-v="turno" aria-selected="true">Promedio por pregunta</button>
 <button type="button" class="wtab" data-v="total" aria-selected="false">Totales acumulados</button>
</div>

<div class="wsort" role="group" aria-label="Ordenar la gráfica" data-vista="turno">
 <button type="button" data-s="r" aria-pressed="true">Por razón</button>
 <button type="button" data-s="a" aria-pressed="false">Por lo que ella responde</button>
 <button type="button" data-s="q" aria-pressed="false">Por lo largo de la pregunta</button>
</div>

<div class="panel" data-vista="turno"><div class="wgrid" id="wgrid">
<div class="wcab"><div>Periodista</div><div>Palabras por pregunta</div><div>Preg.</div>
<div>Resp.</div><div>Razón</div></div>
{''.join(turno)}
<div class="wejew"><div></div><div class="weje">{eje}</div>
<div></div><div></div><div></div></div>
</div>
<p class="wleg"><span><s style="background:var(--papel);border:2px solid var(--p3)"></s>
palabras de su pregunta</span>
<span><s style="background:var(--p5)"></s>palabras de la respuesta</span></p></div>

<div class="panel" data-vista="total" hidden><div class="tgrid">
<div class="tcab"><div>Periodista</div><div>Palabras en total, en miles · ordenado por lo que ella responde</div>
<div>Preg.</div><div>Resp.</div><div>Razón</div></div>
{''.join(tot)}
<div class="tejew"><div></div><div class="weje">{ejet}</div>
<div></div><div></div><div></div></div>
</div>
<p class="wleg"><span><s style="background:var(--papel);border:2px solid var(--p3)"></s>palabras que él o ella pregunta</span>
<span><s style="background:var(--p5)"></s>palabras que ella le responde</span>
<span>en miles · los 100 juntos: {q100 / 1e6:.2f} M preguntadas, {w100 / 1e6:.2f} M respondidas</span></p></div>

<div class="aviso"><p><b>Cuidado con la columna de razón: mide sobre todo qué tan largo habla el
periodista.</b> El largo de la pregunta explica la razón mucho mejor que el largo de la respuesta
(r&nbsp;=&nbsp;{rq:.2f} contra {ra:+.2f}), y el denominador se mueve más que el numerador: las preguntas
van de {q.min():.0f} a {q.max():.0f} palabras, un factor de {q.max() / q.min():.1f}; las respuestas de {a.min():.0f} a {a.max():.0f}, un factor de {a.max() / a.min():.1f}.
Quien hace las preguntas más largas de los 100, {e(largo)}, no queda abajo porque lo traten mal,
sino por el largo de sus preguntas. Es lo que muestra la gráfica de abajo.</p></div>

<h3 class="wsub">3 · Por qué la razón engaña</h3>
<p class="nota">Cada punto es uno de los 100 periodistas. A la derecha, los que hacen preguntas
largas; arriba, aquellos cuya razón es alta. Si la razón midiera trato preferente, los puntos
estarían regados sin forma. Caen en diagonal.</p>

<div class="panel disp">
<svg viewBox="0 0 700 400" role="img"
 aria-label="Dispersión: mientras más larga la pregunta, menor la razón respuesta sobre pregunta">
 {grid}
 <line class="tend" x1="{SX(xmin):.1f}" y1="{SY(m_ * xmin + b_):.1f}" x2="{SX(x2):.1f}" y2="{SY(m_ * x2 + b_):.1f}"/>
 {puntos}
 {nombres}
 <text class="esq" x="594" y="38" text-anchor="end">preguntan corto,</text>
 <text class="esq" x="594" y="51" text-anchor="end">reciben mucho más</text>
 <text class="ejet" x="331" y="388" text-anchor="middle">
  Palabras que él o ella usa al preguntar →</text>
 <text class="ejet" x="15" y="187" text-anchor="middle"
  transform="rotate(-90 15 187)">Razón respuesta / pregunta</text>
 <text class="ejet" x="610" y="381.9">r = {rq:.2f}</text>
 <text class="esq" x="610" y="394.9">tendencia</text>
</svg>
<p class="wleg">Los diez puntos oscuros —las cinco razones más altas y las cinco más bajas— están
etiquetados; los demás tienen su nombre al pasar el cursor.</p></div>

<div class="aviso"><p><b>La medida limpia es palabras por respuesta.</b> Esa no
depende del estilo de quien pregunta, y aun así varía {a.max() / a.min():.1f} veces. Los que reciben respuestas más
largas: {largos}. Los más cortos: {cortos}. La mediana está en {np.median(a):.0f}. Ese es el orden del segundo botón.</p></div>

<div class="aviso"><p><b>Y aun así, esto no mide trato preferente.</b> Faltan tres controles. El
<b>tema</b>: una pregunta técnica de salud obliga a una respuesta larga sin que eso sea deferencia
hacia quien la hizo. El <b>número de preguntas por tanda</b>: quien acumula cinco preguntas antes
de la respuesta recibe una sola contestación para las cinco. Y <b>a quién le dan la palabra</b>, que
no es aleatorio y que la presidenta decide en voz alta. Una respuesta larga puede ser atención,
evasión o clase magistral: <b>ninguna pregunta está clasificada por postura</b> en esta página, así que el
largo no distingue entre las tres.</p></div>
"""


# ------------------------------------------------------ 7 · revisar

FORMAS_TXT = {
    "compromiso": ("Lo promete", "«con gusto lo revisamos», «vamos a revisarlo»"),
    "en_curso": ("Dice que ya está en proceso", "«se está revisando», «se está viendo», «estamos analizando»"),
    "necesidad": ("Dice que hay que revisarlo", "«hay que revisarlo», «tendría que revisarse»"),
    "encargo": ("Se lo encarga a alguien", "«que lo revise la Fiscalía», «le pedí que revisara»"),
    "hecho": ("Dice que ya se revisó", "«ya lo revisamos»"),
    "otra": ("Otro uso", "descripciones y trámites: «se revisa permanentemente»"),
}
SUJ_TXT = {"nosotros": ("Ella o su gobierno", "«estamos analizando»"),
           "tercero": ("Otra persona o institución", "«lo está evaluando el canciller»"),
           "impersonal": ("Sin sujeto", "«se está viendo»")}


def barra(nombre, sub, n, base, mx, tibia=False) -> str:
    s = f"<span>{sub}</span>" if sub else ""
    return (f'<div class="rvf{" tibia" if tibia else ""}"><div><b>{nombre}</b>{s}</div><div class="rvbar"><i style="width:{100 * n / mx:.1f}%"></i></div>'
            f'<div class="rvn f">{n_(n)}</div><div class="rvn">{pct(n, base)}</div></div>')


def s_revisar(D) -> str:
    nc, meses = D["nombre_cat"], D["meses"]
    contesto = [ic for ic in D["ics"] if ic["ella"]]
    R = []
    for ic in contesto:
        hs = [x for t in ic["ella"] for x in hallazgos(t)]
        if hs:
            R.append({"ic": ic, "forma": min((f for _, _, f, _ in hs), key=RANGO.index),
                      "verbos": {v for _, v, _, _ in hs}, "suj": {s for *_, s in hs if s}})
    prom = [x for x in R if x["forma"] in PROMESA]
    tasa = len(prom) / len(contesto)

    formas = collections.Counter(x["forma"] for x in R)
    mxf = max(formas.values())
    hf = "".join(barra(*FORMAS_TXT[k], formas[k], len(R), mxf, tibia=k not in PROMESA) for k in RANGO)
    verbos = collections.Counter(v for x in R for v in x["verbos"])
    mxv = max(verbos.values())
    hv = "".join(barra(v, "", n, len(R), mxv) for v, n in verbos.most_common())
    ger = [x for x in R if x["suj"]]
    suj = collections.Counter(s for x in ger for s in x["suj"])
    mxs = max(suj.values())
    hs = "".join(barra(*SUJ_TXT[k], suj[k], len(ger), mxs) for k in ["nosotros", "tercero", "impersonal"])

    den = collections.Counter(ic["mes"] for ic in contesto)
    num = collections.Counter(x["ic"]["mes"] for x in prom)
    cpm = collections.Counter(c[:7] for c in D["confs"])
    tasas = [num[m] / den[m] if den[m] else 0 for m in meses]
    mxt = max(tasas)
    barras = "".join(
        f'<div class="rvb{" parcial" if cpm[m] < 15 else ""}" tabindex="0" style="height:{100 * t / mxt:.1f}%" '
        f'data-t="{etiqueta_mes(m, True)} · {num[m]} de {den[m]} respuestas · {100 * t:.1f}%'
        f'{f" · mes incompleto: {cpm[m]} conferencias" if cpm[m] < 15 else ""}"><em>{round(100 * t)}</em></div>'
        for m, t in zip(meses, tasas))
    ejes = "".join(f'<span>{MES[int(m[5:]) - 1][0]}{f"<b>{m[:4]}</b>" if m.endswith("-01") or m == meses[0] else ""}</span>' for m in meses)
    ini = sum(num[m] for m in meses[:3]) / sum(den[m] for m in meses[:3])
    fin = sum(num[m] for m in meses[-4:]) / sum(den[m] for m in meses[-4:])

    cats = collections.Counter(nc.get(x["ic"]["cat"], "Sin clasificar") for x in prom)
    mxc = max(cats.values())
    hc = "".join(f'<div class="rvc"><span>{e(k)}</span><div class="rvbar"><i style="width:{100 * v / mxc:.1f}%"></i></div><span class="rvn">{v}</span></div>'
                 for k, v in cats.most_common())
    (cat1, n1), = cats.most_common(1)

    pp = collections.Counter(x["ic"]["per"] for x in prom if x["ic"]["per"])
    cp = collections.Counter(ic["per"] for ic in contesto if ic["per"])
    filas = "".join(
        f'<div class="rvp">{qui(p, D["P"][p]["medio"], "q")}<div class="rvtasa"><i style="width:{min(100, 100 * v / cp[p] / .2):.1f}%"></i>'
        f'<s style="left:{100 * tasa / .2:.1f}%"></s></div><div class="rvn f">{v}</div><div class="rvn">{cp[p]}</div>'
        f'<div class="rvn">{pct(v, cp[p])}</div></div>' for p, v in pp.most_common(10))
    m0, m1 = meses[0], meses[-1]
    return f"""<h2 id="revisar">Revisar, ver, analizar: lo que dijo que estaba en proceso</h2>
<p class="nota">De las <strong>{n_(len(contesto))} preguntas</strong> que contestó Claudia Sheinbaum ella misma, en <strong>{n_(len(R))}</strong> usó «revisar» en alguna forma o dijo que se estaba viendo, analizando o investigando algo. En <strong>{n_(len(prom))}</strong> lo dijo como promesa, como encargo, como necesidad o como un proceso que ya estaba en curso.</p>
<div class="hero"><div><b>{n_(len(prom))}</b><span>preguntas recibieron una promesa o un aviso de proceso</span></div><div><b>{100 * tasa:.1f}%</b><span>de las preguntas que contestó ella misma</span></div><div><b>{pct(n1, len(prom))}</b><span>fueron sobre {e(cat1.lower())}, el tema más frecuente</span></div></div>
<p class="wsub">Cómo lo dijo</p>
<p class="nota">Cada pregunta cuenta una vez, con la forma más comprometida que tuvo la respuesta. Las cuatro primeras suman la cifra de arriba.</p>
<div class="rvfcab"><div>Forma</div><div>Preguntas</div><div>N</div><div>%</div></div>
{hf}
<p class="rvsuma">Porcentaje sobre las <b>{n_(len(R))}</b> preguntas donde usó alguno de los verbos.</p>
<p class="wsub">Con qué verbo</p>
<p class="nota">«Revisar» en cualquier forma. Los demás verbos de indagación solo cuentan en construcción de gerundio («se está viendo», «estamos analizando»). Quedan fuera «vamos a ver», que es muletilla, y «estamos trabajando», que es demasiado genérico. Una pregunta puede tener más de un verbo.</p>
<div class="rvfcab"><div>Verbo</div><div>Preguntas</div><div>N</div><div>%</div></div>
{hv}
<p class="wsub">Quién lo hace</p>
<p class="nota">En las {n_(len(ger))} preguntas donde dijo «está(n) + gerundio», quién actúa cambia lo que la oración afirma: «estamos analizando» compromete a su gobierno; «lo está evaluando el canciller» manda la respuesta a otra institución.</p>
<div class="rvfcab"><div>Sujeto</div><div>Preguntas</div><div>N</div><div>%</div></div>
{hs}
<p class="rvsuma">Porcentaje sobre las <b>{n_(len(ger))}</b> preguntas con gerundio; una pregunta puede caer en más de un sujeto.</p>
<p class="wsub">Mes a mes</p>
<p class="nota">Porcentaje de las preguntas que contestó ella misma en cada mes. El denominador ya descuenta que algunos meses hay más preguntas. En los tres primeros meses la promesa o el aviso de proceso aparecía en una de cada {round(1 / ini)} respuestas; en los cuatro últimos, en una de cada {round(1 / fin)}.</p>
<div class="rvgraf"><div style="--nm:{len(meses)}"><div class="rvmes" role="img" aria-label="Porcentaje mensual de respuestas con promesa o aviso de proceso, de {MES_LARGO[int(m0[5:]) - 1]} de {m0[:4]} a {MES_LARGO[int(m1[5:]) - 1]} de {m1[:4]}">{barras}</div><div class="rvejes">{ejes}</div></div></div>
<p class="rvsuma">La cifra sobre cada barra es el porcentaje redondeado; el cursor da el conteo exacto.</p>
<p class="wsub">Sobre qué tema era la pregunta</p>
<p class="nota">Las {n_(len(prom))} preguntas con promesa o aviso de proceso, por la categoría temática de la pregunta.</p>
<div class="rvcats">{hc}</div>
<p class="wsub">A quién se lo dijo</p>
<p class="nota">Los diez periodistas que más promesas o avisos de proceso recibieron. La barra es qué parte de sus preguntas contestadas por la presidenta terminó así (la escala llega a 20%); la línea negra es el promedio de todos, {100 * tasa:.1f}%.</p>
<div class="tabla-env"><div class="rvpgrid"><div class="rvpcab"><div>Periodista</div><div>% de sus preguntas</div><div>Prom.</div><div>Contest.</div><div>%</div></div>{filas}</div></div>
<div class="aviso"><p><b>Cómo se contó y qué no dice.</b> Se buscó solo en las palabras de la presidenta, no en las de Harfuch o Ebrard dentro del mismo intercambio, ni la palabra «revisión», que aparece sobre todo por el T-MEC. La forma y el sujeto se asignan con reglas gramaticales sobre las palabras que rodean al verbo, no con un modelo, y fallan en una minoría de casos, como cuando cita a otro («Trump dijo: hay que revisarlo»); su precisión no se ha medido con una muestra codificada a mano. Mide qué se dijo, no si la revisión ocurrió. Y «en proceso» no es lo mismo que evadir: muchas de estas oraciones informan algo concreto y en otras quien actúa es otra institución. El corpus no marca cuáles son una manera de no responder.</p></div>
<p class="nota">Cada una de las {n_(len(R))} preguntas, con la oración exacta, el verbo, el sujeto y el enlace a la estenográfica, se consulta en el buscador.<br><a class="rvir" href="index.html#revisar" target="_top">Abrir «Revisar y procesos en curso» en el buscador ↗</a></p>
"""


# ------------------------------------------------------- 8 · dinero

def s_dinero(D) -> str:
    # Medios por clave: el puente guarda la declaración cruda («revista Contralínea»).
    nombre_por_clave = {}
    for h in D["hilos"]:
        for m in h["medios"]:
            nombre_por_clave.setdefault(canonizar.clave(m), m)
    claves_hilo = [{canonizar.clave(m) for m in h["medios"]} for h in D["hilos"]]

    filas = []
    with (paths().root / "config" / "puente_medios.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cl = {canonizar.clave(c) for c in canonizar.partir_medios(r["medio_hablado"])}
            n = sum(1 for ch in claves_hilo if ch & cl)
            nombre = " / ".join(nombre_por_clave[c] for c in cl if c in nombre_por_clave) or r["medio_hablado"]
            filas.append({**r, "n": n, "nombre": nombre, "claves": cl, "monto": float(r["monto_2024_2026"] or 0)})
    mxm = max(f["monto"] for f in filas)

    def tabla(conf, cls):
        fs = sorted((f for f in filas if f["confianza"] == conf), key=lambda f: (-f["monto"], -f["n"]))
        out = []
        for f in fs:
            monto = f"{f['monto'] / 1e6:.1f} M" if f["monto"] else "—"
            barra_ = f'<i style="width:{round(100 * f["monto"] / mxm)}%"></i>' if f["monto"] else ""
            out.append(f'<tr class="{cls}"><td>{e(f["nombre"])}</td><td class="n">{f["n"]}</td>'
                       f'<td class="n">{monto}</td><td><span class="mb">{barra_}</span></td>'
                       f'<td class="rs">{e(f["beneficiario_canonico"][:52])}</td></tr>')
        return "".join(out)

    # Un medio ya pareado no está «sin investigar» aunque el puente lo traiga con otra grafía.
    pareadas = {c for f in filas if f["confianza"] != "pendiente" for c in f["claves"]}
    pend = sorted((f for f in filas if f["confianza"] == "pendiente" and not f["claves"] & pareadas),
                  key=lambda f: -f["n"])
    hp = "".join(f'<div><b>{f["n"]}</b> {e(f["nombre"])}</div>' for f in pend)
    cab = ('<table><thead><tr><th>Medio</th><th class="n">Interv.</th><th class="n">2024–26</th>'
           '<th></th><th>Cobra como</th></tr></thead>')
    h3 = ('<h3 style="font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--suave);'
          'margin:{m};font-weight:600">{t}</h3>')
    return f"""<h2>El dinero: publicidad oficial</h2>
<p class="nota">Cruce con un segundo proyecto: el gasto federal en comunicación social,
2012–2026, de la Secretaría Anticorrupción. La pregunta es si los medios que reciben la palabra
son también los que reciben dinero. El dinero es el de <strong>octubre de 2024 a mayo de 2026</strong>,
donde traslapan los dos conjuntos de datos; las intervenciones cuentan todo el corpus, hasta el {fecha_larga(D['corte'])}.</p>

<div class="din">
{h3.format(m='22px 0 0', t='Verificados a mano')}
{cab}
<tbody>{tabla('alta', 'conf')}</tbody></table>

{h3.format(m='26px 0 0', t='Pareados automáticamente · falta revisarlos')}
{cab}
<tbody>{tabla('media', '')}</tbody></table>
</div>

<div class="aviso"><p><b>Proceso dejó de recibir dinero federal en 2021.</b> No es que no se le
encuentre: recibió 37.8 millones entre 2012 y 2021, y desde entonces cero. Todo el periodo que
cubre este corpus cae después de ese corte.</p>
</div>

{h3.format(m='26px 0 8px', t=f'Sin investigar todavía ({len(pend)})')}
<p class="nota"><strong>Que no aparezcan aquí no significa que no cobren.</strong> Puede ser que
cobren bajo una razón social irreconocible, como Contralínea; que cobren de gobiernos estatales o
municipales, que este conjunto de datos <em>no cubre</em> porque es solo federal; o que en efecto
no cobren. Distinguir esas tres cosas es trabajo humano, medio por medio.</p>
<div class="pend">{hp}</div>

<div class="aviso"><p><b>Cómo NO leer esto.</b> Estos números invitan la conclusión «a quien le
pagan pregunta más suave». El dato no la sostiene, por tres razones. Es una <b>asociación
descriptiva</b>, no causal. El tamaño de la audiencia empuja a la vez el gasto publicitario y la
probabilidad de que te den la palabra, y ese confusor no está controlado. Y sobre todo:
<b>ninguna pregunta está clasificada por postura</b> en esta página, así que solo se puede cruzar dinero
contra <i>frecuencia</i>, nunca contra <i>dureza</i>.</p></div>
"""


# ------------------------------------------------------- 9 · tabla

def s_tabla(D) -> str:
    P = D["P"]
    filas = []
    for p in ranking(D):
        d = P[p]
        if d["interv"] < 6:
            break
        fs = sorted(d["fechas"])
        filas.append(f'<tr><td>{e(p)}</td><td>{e(d["medio"])}</td><td class="n">{d["interv"]}</td><td class="n">{d["preg"]}</td>'
                     f'<td class="n">{d["preg"] / d["interv"]:.1f}</td><td class="n">{fs[0]}</td><td class="n">{fs[-1]}</td>'
                     f'<td class="n">{len(d["meses"])}</td></tr>')
    return f"""<h2>Los datos</h2>
<p class="nota">Los {len(filas)} periodistas con seis intervenciones o más.</p>
<div class="tabla-env"><table>
<thead><tr><th>Periodista</th><th>Medio</th><th class="n">Intervenciones</th>
<th class="n">Preguntas</th><th class="n">Preg/interv</th><th class="n">Primera</th>
<th class="n">Última</th><th class="n">Meses activos</th></tr></thead>
<tbody>{''.join(filas)}</tbody></table></div>

<p class="nota"><strong>Preguntas por intervención</strong> es la columna que más dice: recibir
la palabra y preguntar mucho son cosas distintas. Hay quien recibe el micrófono más veces que
otro y aun así pregunta menos de la mitad cada vez.</p>

<p class="nota" style="font-size:13px">Los nombres de persona y de medio están canonizados, con las dudas resueltas a mano. Contra un conteo manual externo del primer semestre de 2026 falta un <b>14%</b> de las tandas, y el faltante no es aleatorio: son personas que reciben la palabra sin decir su nombre, y a quienes la estenográfica no permite identificar. Mide concesión de turnos, no postura: ninguna pregunta está clasificada por postura en esta página.</p>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hasta", default="2026-09-30", help="última conferencia que entra (AAAA-MM-DD)")
    args = ap.parse_args()

    plantilla = paths().root / "assets" / "exploracion_plantilla.html"
    html_ = plantilla.read_text(encoding="utf-8")
    for m in ("{{CUERPO}}", "{{TEMAS_D}}", "{{NM}}", "{{RANGO_MESES}}"):
        if m not in html_:
            raise SystemExit(f"La plantilla no trae el marcador {m}")

    D = cargar(args.hasta)
    temas_mes, datos_mes = s_temas_mes(D)
    cuerpo = "\n".join([s_calor(D), s_concentracion(D), s_treemap(D), s_temas(D), temas_mes,
                        s_dendrograma(D), s_palabras(D), s_revisar(D), s_dinero(D), s_tabla(D)])
    m0, m1 = D["meses"][0], D["meses"][-1]
    rango = f"de {MES_LARGO[int(m0[5:]) - 1]} de {m0[:4]} a {MES_LARGO[int(m1[5:]) - 1]} de {m1[:4]}"
    html_ = (html_.replace("{{NM}}", str(len(D["meses"]))).replace("{{RANGO_MESES}}", rango)
             .replace("{{TEMAS_D}}", datos_mes).replace("{{CUERPO}}", cuerpo))

    destino = paths().outputs / "quien_pregunta.html"
    destino.write_text(html_, encoding="utf-8")
    print(f"Corte:         {args.hasta}  ({len(D['confs'])} conferencias, {D['confs'][0]} a {D['confs'][-1]})")
    print(f"Tandas:        {len(D['hilos']):,}   preguntas útiles: {len(D['ics']):,}   periodistas: {len(D['P']):,}")
    print(f"Página:        {destino.stat().st_size / 1e6:.2f} MB")
    print(f"Escrito: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
