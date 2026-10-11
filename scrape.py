"""Collecte les séances des cinémas de la métropole lilloise (source : AlloCiné)
et écrit data.json, lu par index.html.

Usage : python scrape.py [nb_jours]   (7 par défaut)
"""
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

CINEMAS = {
    "P0086": ("UGC Ciné Cité", "Lille"),
    "P0022": ("Le Métropole", "Lille"),
    "P0047": ("Le Majestic", "Lille"),
    "P9369": ("L'Univers", "Lille"),
    "W5902": ("L'Hybride", "Lille"),
    "P0665": ("Kinepolis", "Lomme"),
    "P1143": ("Kino Ciné", "Villeneuve-d'Ascq"),
    "P0200": ("Le Méliès", "Villeneuve-d'Ascq"),
    "G02AS": ("Megarama", "Roubaix"),
    "P6549": ("Le Fresnoy", "Tourcoing"),
    "W5920": ("Les Écrans", "Tourcoing"),
    "P0953": ("Colisée Lumière", "Marcq-en-Barœul"),
    "W5970": ("Le Pont des Arts", "Marcq-en-Barœul"),
    "P0949": ("Ciné Lambersart", "Lambersart"),
    "P5441": ("Gérard Philipe", "Wasquehal"),
    "G0G21": ("Les Lumières", "Armentières"),
    "P1422": ("Le Familia", "Halluin"),
}

URL = "https://www.allocine.fr/_/showtimes/theater-{cid}/d-{day}/p-{page}/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lille-cine/1.0"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # réseau ou JSON invalide : on réessaie
            if attempt == 2:
                print(f"  échec {url}: {e}", file=sys.stderr)
                return None
            time.sleep(2)


def person(p):
    return " ".join(x for x in (p.get("firstName"), p.get("lastName")) if x)


def release_date(m):
    for r in m.get("releases") or []:
        if "THEATER" in ((r.get("releaseTags") or {}).get("tagTypes") or []):
            return (r.get("releaseDate") or {}).get("date")
    return None


def film_info(m):
    stats = m.get("stats") or {}
    cast = [person(e["node"]["actor"]) for e in ((m.get("cast") or {}).get("edges") or [])
            if (e.get("node") or {}).get("actor")][:4]
    return {
        "t": m.get("title"),
        "ot": m.get("originalTitle"),
        "y": (m.get("data") or {}).get("productionYear"),
        "r": release_date(m),
        "d": [person(c["person"]) for c in m.get("credits") or []
              if (c.get("position") or {}).get("name") == "DIRECTOR" and c.get("person")],
        "c": cast,
        "rt": m.get("runtime"),
        "g": [g.get("translate") for g in m.get("genres") or []],
        "co": [c.get("localizedName") for c in m.get("countries") or []],
        "lang": m.get("languages") or [],
        "p": (m.get("poster") or {}).get("url"),
        "ps": (stats.get("pressReview") or {}).get("score"),
        "us": (stats.get("userRating") or {}).get("score"),
        "uc": (stats.get("userRating") or {}).get("count"),
        "syn": m.get("synopsis"),
    }


def version(s, french):
    tags = s.get("tags") or []
    if "Localization.Version.French" in tags and not french:
        return "VF"
    if "Localization.Version.Original" in tags and not french:
        return "VO"
    return ""


def formats(s):
    out = []
    for t in s.get("tags") or []:
        low = t.lower()
        for key, label in (("imax", "IMAX"), ("3d", "3D"), ("4dx", "4DX"), ("screenx", "ScreenX"),
                           ("dolby", "Dolby"), ("icetheatre", "ICE"), ("70mm", "70mm"), ("35mm", "35mm")):
            if key in low and label not in out:
                out.append(label)
    return out


def ticket(s):
    for t in ((s.get("data") or {}).get("ticketing") or []):
        if t.get("provider") == "default" and t.get("urls"):
            return t["urls"][0]
    return None


def fetch_posters(films, folder):
    """Télécharge une miniature locale par film (les images externes ne sont pas toujours autorisées)."""
    folder.mkdir(exist_ok=True)
    for fid, f in films.items():
        url, dest = f.pop("p", None), folder / f"{fid}.jpg"
        if url and not dest.exists():
            try:
                req = urllib.request.Request(url.replace("/img/", "/r_160_240/img/", 1), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dest.write_bytes(r.read())
            except Exception as e:
                print(f"  affiche {fid}: {e}", file=sys.stderr)
        if dest.exists():
            f["p"] = f"posters/{fid}.jpg"


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    today = date.today()
    films, shows = {}, []
    for cid, (name, city) in CINEMAS.items():
        print(f"{name} ({city})")
        for i in range(days):
            day = (today + timedelta(days=i)).isoformat()
            page, total = 1, 1
            while page <= total:
                data = get(URL.format(cid=cid, day=day, page=page))
                if not data or data.get("error"):
                    break
                total = (data.get("pagination") or {}).get("totalPages") or 1
                for res in data.get("results") or []:
                    m = res.get("movie") or {}
                    fid = str(m.get("internalId"))
                    if fid not in films:
                        films[fid] = film_info(m)
                    french = "FRENCH" in (m.get("languages") or [])
                    for lst in (res.get("showtimes") or {}).values():
                        for s in lst or []:
                            row = {"f": fid, "c": cid, "at": s["startsAt"][:16], "v": version(s, french)}
                            fm = formats(s)
                            if fm:
                                row["fm"] = fm
                            if s.get("isPreview"):
                                row["ap"] = 1
                            tk = ticket(s)
                            if tk:
                                row["tk"] = tk
                            shows.append(row)
                page += 1
                time.sleep(0.3)
    fetch_posters(films, Path(__file__).with_name("posters"))
    shows.sort(key=lambda s: (s["at"], s["c"]))
    out = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "cinemas": {cid: {"n": n, "v": v} for cid, (n, v) in CINEMAS.items()},
        "films": films,
        "shows": shows,
    }
    path = Path(__file__).with_name("data.json")
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(films)} films, {len(shows)} séances -> {path}")


if __name__ == "__main__":
    main()
