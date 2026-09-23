import * as THREE from "three";
import { ResourceDisposer } from "../../core/ResourceDisposer.js";

const COLORS = Object.freeze(["#6f879b", "#9b826e", "#7d927f", "#8d8096", "#6e9295"]);

function finitePairs(series) {
  return (series?.x || []).map((x, index) => [Number(x), Number(series?.y?.[index])])
    .filter(([x, y]) => Number.isFinite(x) && Number.isFinite(y));
}

function range(values) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, span: max === min ? 1 : max - min };
}

function lineMaterial(color, opacity = 1) {
  return new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity });
}

function meshMaterial(color, opacity = 1) {
  return new THREE.MeshStandardMaterial({
    color, metalness: 0, roughness: 0.86, transparent: opacity < 1, opacity,
  });
}

export class EvidenceThreeScene {
  constructor(config) {
    this.config = config;
    this.group = new THREE.Group();
    this.group.name = `${config.slug}_three_evidence_scene`;
    this.boundsObjects = [];
  }

  build(contract) {
    this.addReferenceFrame();
    if (this.config.sceneType === "template") this.addTemplatePlane();
    else if ((contract.series || []).some((item) => finitePairs(item).length)) this.addSeries(contract.series);
    else this.addTableBars(contract.table);
    return this.group;
  }

  addReferenceFrame() {
    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(8.4, 5.6),
      new THREE.MeshStandardMaterial({ color: "#dde4e4", metalness: 0, roughness: 1, transparent: true, opacity: 0.5, side: THREE.DoubleSide }),
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -0.05;
    plane.name = "evidence_reference_plane";
    this.group.add(plane);
    this.boundsObjects.push(plane);

    const grid = new THREE.GridHelper(8, 8, "#9eb0b5", "#c8d2d3");
    grid.position.y = 0;
    grid.material.transparent = true;
    grid.material.opacity = 0.48;
    this.group.add(grid);

    const axes = [
      [[-4, 0.02, 2.6], [4, 0.02, 2.6]],
      [[-4, 0.02, -2.6], [-4, 3.8, -2.6]],
      [[-4, 0.02, -2.6], [-4, 0.02, 2.6]],
    ];
    axes.forEach((points) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(points.map((point) => new THREE.Vector3(...point)));
      this.group.add(new THREE.Line(geometry, lineMaterial("#7c8f99", 0.8)));
    });
  }

  addSeries(seriesList) {
    const usable = seriesList.map((item) => ({ item, points: finitePairs(item) })).filter(({ points }) => points.length);
    const xValues = usable.flatMap(({ points }) => points.map(([x]) => x));
    const yValues = usable.flatMap(({ points }) => points.map(([, y]) => y));
    const xr = range(xValues);
    const yr = range(yValues);

    usable.forEach(({ item, points }, seriesIndex) => {
      const z = usable.length === 1 ? 0 : -1.5 + (3 * seriesIndex) / Math.max(usable.length - 1, 1);
      const sampled = points.filter((_, index) => index % Math.max(Math.floor(points.length / 180), 1) === 0 || index === points.length - 1);
      const vertices = sampled.map(([x, y]) => new THREE.Vector3(
        -3.7 + 7.4 * ((x - xr.min) / xr.span),
        0.18 + 3.25 * ((y - yr.min) / yr.span),
        z,
      ));
      const geometry = new THREE.BufferGeometry().setFromPoints(vertices);
      const color = item.color || COLORS[seriesIndex % COLORS.length];
      const line = new THREE.Line(geometry, lineMaterial(color));
      line.name = `evidence_series_${seriesIndex}`;
      this.group.add(line);
      this.boundsObjects.push(line);

      const markerGeometry = new THREE.SphereGeometry(0.055, 10, 8);
      const markerMaterial = meshMaterial(color);
      vertices.filter((_, index) => index % Math.max(Math.floor(vertices.length / 14), 1) === 0).forEach((point) => {
        const marker = new THREE.Mesh(markerGeometry, markerMaterial);
        marker.position.copy(point);
        marker.userData.sharedGeometry = true;
        this.group.add(marker);
      });
    });
  }

  addTableBars(table = {}) {
    const rows = (table.rows || []).slice(0, 24);
    const values = rows.map((row) => row.map(Number).filter(Number.isFinite)).filter((row) => row.length);
    if (!values.length) {
      this.addTemplatePlane();
      return;
    }
    const scalar = values.map((row) => row[row.length - 1]);
    const vr = range(scalar);
    const columns = Math.ceil(Math.sqrt(scalar.length));
    scalar.forEach((value, index) => {
      const height = 0.32 + 3 * ((value - vr.min) / vr.span);
      const geometry = new THREE.BoxGeometry(0.62, height, 0.62);
      const material = meshMaterial(COLORS[index % COLORS.length], 0.9);
      const bar = new THREE.Mesh(geometry, material);
      bar.position.set(-3.1 + (index % columns) * 1.05, height / 2, -1.7 + Math.floor(index / columns) * 1.05);
      bar.name = `evidence_sample_${index}`;
      this.group.add(bar);
      this.boundsObjects.push(bar);
    });
  }

  addTemplatePlane() {
    const slab = new THREE.Mesh(new THREE.BoxGeometry(6.4, 0.3, 3.7), meshMaterial("#b8c7cc", 0.92));
    slab.position.y = 0.24;
    slab.name = "template_reference_slab";
    this.group.add(slab);
    this.boundsObjects.push(slab);
    const arrow = new THREE.ArrowHelper(new THREE.Vector3(0, -1, 0), new THREE.Vector3(0, 3.4, 0), 2.35, "#7d8fa0", 0.28, 0.14);
    arrow.name = "template_incident_direction";
    this.group.add(arrow);
    this.boundsObjects.push(arrow);
  }

  getBounds() {
    const bounds = new THREE.Box3();
    this.boundsObjects.forEach((object) => bounds.expandByObject(object));
    return bounds;
  }

  dispose() {
    ResourceDisposer.disposeObject(this.group);
    this.boundsObjects = [];
  }
}
