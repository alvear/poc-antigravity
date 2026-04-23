import os, json, subprocess, uuid

# archi_helper nao usa variaveis de ambiente - apenas paths locais.
# Mantemos config import para consistencia e futura extensao.
MODELS_DIR = os.path.join(os.path.dirname(__file__), "archi_models")
os.makedirs(MODELS_DIR, exist_ok=True)

def nid():
    return "id-" + uuid.uuid4().hex[:24]

def generate_technical_view(name, config):
    ids       = {}   # element_name -> element_id
    view_ids  = {}   # element_name -> view_child_id

    # Channels
    channel_els = []
    for ch in config.get("channels", []):
        eid = nid()
        ids[ch] = eid
        channel_els.append((eid, ch, "archimate:ApplicationComponent"))

    # GKE node
    gke_name = config.get("gcp", {}).get("gke_cluster", "Google Cloud Platform")
    gke_id   = nid()
    ids[gke_name] = gke_id

    # Services
    service_els = []
    for svc in config.get("gcp", {}).get("services", []):
        svc_id = nid()
        ep_id  = nid()
        ids[svc["name"]]            = svc_id
        ids[svc.get("endpoint","")] = ep_id
        service_els.append({
            "svc_id":   svc_id,
            "svc_name": svc["name"],
            "ep_id":    ep_id,
            "ep_name":  svc.get("endpoint","")
        })

    # Database
    db_name = config.get("gcp",{}).get("database","")
    db_id   = nid()
    if db_name:
        ids[db_name] = db_id

    # External
    ext_els = []
    for ext in config.get("external",[]):
        eid = nid()
        ids[ext] = eid
        ext_els.append((eid, ext, "archimate:ApplicationComponent"))

    # --- Relations (folder) ---
    rel_lines = []
    rel_ids   = {}   # key -> relation_id

    # PEGA -> cada servico (triggering)
    for s in service_els:
        if channel_els:
            rid = nid()
            rel_ids[f"ch_to_{s['svc_name']}"] = rid
            rel_lines.append(f'    <element xsi:type="archimate:TriggeringRelationship" id="{rid}" source="{channel_els[0][0]}" target="{s["svc_id"]}"/>')

    # Cada servico -> PEGA de volta (serving)
    for s in service_els:
        if channel_els:
            rid = nid()
            rel_ids[f"{s['svc_name']}_to_ch"] = rid
            rel_lines.append(f'    <element xsi:type="archimate:ServingRelationship" id="{rid}" source="{s["svc_id"]}" target="{channel_els[0][0]}"/>')

    # Servico -> endpoint (composicao)
    for s in service_els:
        rid = nid()
        rel_ids[f"{s['svc_name']}_comp_ep"] = rid
        rel_lines.append(f'    <element xsi:type="archimate:CompositionRelationship" id="{rid}" source="{s["svc_id"]}" target="{s["ep_id"]}"/>')

    # Primeiro servico -> external
    if ext_els and service_els:
        rid = nid()
        rel_ids["svc_to_ext"] = rid
        rel_lines.append(f'    <element xsi:type="archimate:AssociationRelationship" id="{rid}" source="{service_els[0]["svc_id"]}" target="{ext_els[0][0]}"/>')

    # Ultimo servico -> database
    if db_name and service_els:
        rid = nid()
        rel_ids["svc_to_db"] = rid
        rel_lines.append(f'    <element xsi:type="archimate:AssociationRelationship" id="{rid}" source="{service_els[-1]["svc_id"]}" target="{db_id}"/>')

    # --- Folder elements ---
    folder_lines = []
    for eid, n, t in channel_els:
        folder_lines.append(f'    <element xsi:type="{t}" name="{n}" id="{eid}"/>')
    folder_lines.append(f'    <element xsi:type="archimate:Node" name="{gke_name}" id="{gke_id}"/>')
    for s in service_els:
        folder_lines.append(f'    <element xsi:type="archimate:ApplicationComponent" name="{s["svc_name"]}" id="{s["svc_id"]}"/>')
        folder_lines.append(f'    <element xsi:type="archimate:ApplicationService" name="{s["ep_name"]}" id="{s["ep_id"]}"/>')
    if db_name:
        folder_lines.append(f'    <element xsi:type="archimate:DataObject" name="{db_name}" id="{db_id}"/>')
    for eid, n, t in ext_els:
        folder_lines.append(f'    <element xsi:type="{t}" name="{n}" id="{eid}"/>')

    # --- VIEW ---
    view_id       = nid()
    view_children = []
    connections   = []

    # Channels (esquerda)
    for i, (eid, cname, atype) in enumerate(channel_els):
        vcid = nid()
        view_ids[cname] = vcid
        y = 120 + i * 140
        view_children.append(
            f'      <child xsi:type="archimate:DiagramObject" id="{vcid}" archimateElement="{eid}">\n'
            f'        <bounds x="40" y="{y}" width="120" height="60"/>\n'
            f'      </child>'
        )

    # GCP container
    gcp_height = max(300, len(service_els) * 120 + 60)
    gcp_vcid   = nid()
    view_ids[gke_name] = gcp_vcid
    gcp_block = (
        f'      <child xsi:type="archimate:DiagramObject" id="{gcp_vcid}" archimateElement="{gke_id}">\n'
        f'        <bounds x="220" y="40" width="500" height="{gcp_height}"/>\n'
    )
    for i, s in enumerate(service_els):
        svc_vcid = nid()
        ep_vcid  = nid()
        view_ids[s["svc_name"]] = svc_vcid
        view_ids[s["ep_name"]]  = ep_vcid
        sy = 40 + i * 115
        gcp_block += (
            f'        <child xsi:type="archimate:DiagramObject" id="{svc_vcid}" archimateElement="{s["svc_id"]}">\n'
            f'          <bounds x="60" y="{sy}" width="370" height="90"/>\n'
            f'          <child xsi:type="archimate:DiagramObject" id="{ep_vcid}" archimateElement="{s["ep_id"]}">\n'
            f'            <bounds x="20" y="30" width="290" height="40"/>\n'
            f'          </child>\n'
            f'        </child>\n'
        )
    gcp_block += '      </child>'
    view_children.append(gcp_block)

    # Database
    if db_name:
        db_vcid = nid()
        view_ids[db_name] = db_vcid
        view_children.append(
            f'      <child xsi:type="archimate:DiagramObject" id="{db_vcid}" archimateElement="{db_id}">\n'
            f'        <bounds x="340" y="{gcp_height + 80}" width="200" height="55"/>\n'
            f'      </child>'
        )

    # External (direita)
    for i, (eid, ename, atype) in enumerate(ext_els):
        evcid = nid()
        view_ids[ename] = evcid
        y = 80 + i * 130
        view_children.append(
            f'      <child xsi:type="archimate:DiagramObject" id="{evcid}" archimateElement="{eid}">\n'
            f'        <bounds x="780" y="{y}" width="160" height="60"/>\n'
            f'      </child>'
        )

    # --- Connections na view ---
    ch_vcid = view_ids.get(channel_els[0][1]) if channel_els else None

    # PEGA -> cada servico (seta para direita)
    for s in service_els:
        svc_vcid = view_ids.get(s["svc_name"])
        rid      = rel_ids.get(f"ch_to_{s['svc_name']}")
        if ch_vcid and svc_vcid and rid:
            conn_id = nid()
            connections.append(
                f'      <connection xsi:type="archimate:Connection" id="{conn_id}" '
                f'source="{ch_vcid}" target="{svc_vcid}" archimateRelationship="{rid}"/>'
            )

    # Servico -> PEGA (seta de retorno)
    for s in service_els:
        svc_vcid = view_ids.get(s["svc_name"])
        rid      = rel_ids.get(f"{s['svc_name']}_to_ch")
        if ch_vcid and svc_vcid and rid:
            conn_id = nid()
            connections.append(
                f'      <connection xsi:type="archimate:Connection" id="{conn_id}" '
                f'source="{svc_vcid}" target="{ch_vcid}" archimateRelationship="{rid}"/>'
            )

    # Primeiro servico -> external
    if ext_els and service_els:
        svc_vcid = view_ids.get(service_els[0]["svc_name"])
        ext_vcid = view_ids.get(ext_els[0][1])
        rid      = rel_ids.get("svc_to_ext")
        if svc_vcid and ext_vcid and rid:
            conn_id = nid()
            connections.append(
                f'      <connection xsi:type="archimate:Connection" id="{conn_id}" '
                f'source="{svc_vcid}" target="{ext_vcid}" archimateRelationship="{rid}"/>'
            )

    # Ultimo servico -> database
    if db_name and service_els:
        svc_vcid = view_ids.get(service_els[-1]["svc_name"])
        db_vcid  = view_ids.get(db_name)
        rid      = rel_ids.get("svc_to_db")
        if svc_vcid and db_vcid and rid:
            conn_id = nid()
            connections.append(
                f'      <connection xsi:type="archimate:Connection" id="{conn_id}" '
                f'source="{svc_vcid}" target="{db_vcid}" archimateRelationship="{rid}"/>'
            )

    view_xml = (
        f'    <element xsi:type="archimate:ArchimateDiagramModel" name="Visao Tecnica" id="{view_id}">\n'
        + "\n".join(view_children) + "\n"
        + "\n".join(connections)   + "\n"
        + "    </element>"
    )

    # Manifest para validacao final
    manifest = {
        "model_name": name,
        "channels":   [ch for _, ch, _ in channel_els],
        "services":   [{"name": s["svc_name"], "endpoint": s["ep_name"]} for s in service_els],
        "external":   [ext for _, ext, _ in ext_els],
        "database":   db_name,
    }
    manifest_file = os.path.join(MODELS_DIR, f"{name.replace(' ','_')}_manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<archimate:model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:archimate="http://www.archimatetool.com/archimate" name="{name}" id="{nid()}" version="5.0.0">
  <folder name="Strategy" id="{nid()}" type="strategy"/>
  <folder name="Business" id="{nid()}" type="business"/>
  <folder name="Application" id="{nid()}" type="application">
{chr(10).join(folder_lines)}
  </folder>
  <folder name="Technology &amp; Physical" id="{nid()}" type="technology"/>
  <folder name="Motivation" id="{nid()}" type="motivation"/>
  <folder name="Implementation &amp; Migration" id="{nid()}" type="implementation_migration"/>
  <folder name="Other" id="{nid()}" type="other"/>
  <folder name="Relations" id="{nid()}" type="relations">
{chr(10).join(rel_lines)}
  </folder>
  <folder name="Views" id="{nid()}" type="diagrams">
{view_xml}
  </folder>
</archimate:model>'''

    arch_file = os.path.join(MODELS_DIR, f"{name.replace(' ','_')}.archimate")
    with open(arch_file, "w", encoding="utf-8") as f:
        f.write(xml)

    result = {"file": arch_file, "manifest": manifest_file, "services": len(service_els)}
    print(json.dumps(result))
    return arch_file, manifest_file

def open_in_archi(filepath):
    archi_paths = [
        r"C:\Program Files\Archi\Archi.exe",
        r"C:\Program Files (x86)\Archi\Archi.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Archi\Archi.exe"),
    ]
    for path in archi_paths:
        if os.path.exists(path):
            subprocess.Popen([path, filepath])
            return
    print("[ARCHI] Abra manualmente:", filepath)
