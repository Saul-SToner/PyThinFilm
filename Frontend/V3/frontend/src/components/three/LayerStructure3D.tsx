import { useEffect, useRef, useState } from "react";
import { Maximize2, Minimize2, Minus, Plus, RotateCcw } from "lucide-react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import { Button } from "@/components/ui/button";
import type { DesignLayer, MaterialOption } from "@/types/design";

interface LayerStructure3DProps {
  layers: DesignLayer[];
  materials: MaterialOption[];
  className?: string;
}

const MATERIAL_COLORS: Record<string, number> = {
  SiO2: 0x72c7df,
  MgF2: 0x8ed7c6,
  Al2O3: 0xdbeafe,
  Ta2O5: 0xf4b85a,
  ZrO2: 0xf59e7a,
  TiO2: 0x7c83e6,
  Si: 0x4b5563,
  Ag: 0xcbd5e1,
  Au: 0xe7ad37,
  Al: 0xaeb8c4,
  Cu: 0xc8754b,
  Cr: 0x71717a,
};

export function LayerStructure3D({ layers, materials, className }: LayerStructure3DProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const resetPositionRef = useRef(new THREE.Vector3(8, 6.5, 9));
  const [isFullscreen, setIsFullscreen] = useState(false);

  function zoom(factor: number) {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;
    const offset = camera.position.clone().sub(controls.target);
    const distance = THREE.MathUtils.clamp(offset.length() * factor, controls.minDistance, controls.maxDistance);
    camera.position.copy(controls.target).add(offset.setLength(distance));
    controls.update();
  }

  function resetView() {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls) return;
    controls.target.set(0, 0, 0);
    camera.position.copy(resetPositionRef.current);
    controls.update();
  }

  async function toggleFullscreen() {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await wrapperRef.current?.requestFullscreen();
  }

  useEffect(() => {
    const update = () => setIsFullscreen(document.fullscreenElement === wrapperRef.current);
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x09131f);
    scene.fog = new THREE.Fog(0x09131f, 13, 24);
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    cameraRef.current = camera;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.enableDamping = true;
    controls.enablePan = true;
    controls.screenSpacePanning = true;
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    controls.mouseButtons.MIDDLE = THREE.MOUSE.DOLLY;
    controls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    controls.touches.ONE = THREE.TOUCH.ROTATE;
    controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
    controls.target.set(0, 0, 0);
    scene.add(new THREE.HemisphereLight(0xc7e9ff, 0x152235, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 2.8);
    key.position.set(5, 8, 6);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x4d9fff, 1.2);
    fill.position.set(-6, 3, -4);
    scene.add(fill);

    const group = new THREE.Group();
    const enabled = layers.filter((layer) => layer.enabled);
    const visualHeights = enabled.map((layer) => THREE.MathUtils.clamp(0.25 + Math.sqrt(Math.max(layer.thickness_nm, 0)) * 0.055, 0.3, 1.7));
    const totalHeight = visualHeights.reduce((sum, value) => sum + value, 0);
    const largestDimension = Math.max(totalHeight + 1.5, 5.8, 4.2);
    const fitDistance = largestDimension / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.15;
    const viewDirection = new THREE.Vector3(8, 6.5, 9).normalize();
    const fittedPosition = viewDirection.multiplyScalar(fitDistance);
    camera.position.copy(fittedPosition);
    resetPositionRef.current.copy(fittedPosition);
    controls.minDistance = Math.max(2.5, fitDistance * 0.35);
    controls.maxDistance = Math.max(22, fitDistance * 4);
    let y = -totalHeight / 2;
    enabled.forEach((layer, index) => {
      const height = visualHeights[index];
      const metadata = materials.find((item) => item.material_id === layer.material_id);
      const color = MATERIAL_COLORS[layer.material_id] ?? (metadata?.category === "金属" ? 0xb7bec8 : 0x6ea8d9);
      const geometry = new THREE.BoxGeometry(5.8, height, 4.2);
      const material = new THREE.MeshPhysicalMaterial({
        color,
        metalness: metadata?.category === "金属" ? 0.72 : 0.05,
        roughness: 0.28,
        transmission: metadata?.category === "介质" ? 0.12 : 0,
        transparent: true,
        opacity: 0.92,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.y = y + height / 2;
      mesh.userData.layerId = layer.id;
      group.add(mesh);
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: 0xe2f3ff, transparent: true, opacity: 0.35 }));
      edges.position.copy(mesh.position);
      group.add(edges);
      y += height;
    });
    scene.add(group);

    const grid = new THREE.GridHelper(18, 18, 0x31516e, 0x1b3147);
    grid.position.y = -totalHeight / 2 - 0.5;
    scene.add(grid);

    let frame = 0;
    const resize = () => {
      const width = Math.max(host.clientWidth, 1);
      const height = Math.max(host.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      cameraRef.current = null;
      controlsRef.current = null;
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments || object instanceof THREE.Line) {
          object.geometry.dispose();
          const objectMaterial = object.material;
          (Array.isArray(objectMaterial) ? objectMaterial : [objectMaterial]).forEach((item) => item.dispose());
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [layers, materials]);

  return (
    <div ref={wrapperRef} className={`relative overflow-hidden bg-[#09131f] ${className ?? ""} ${isFullscreen ? "h-screen w-screen" : ""}`} aria-label="膜系三维结构">
      <div ref={hostRef} className="absolute inset-0" />
      <div className="absolute right-3 top-3 z-10 flex gap-1 rounded-md border border-white/15 bg-black/35 p-1 backdrop-blur">
        <Button variant="ghost" size="icon" className="size-8 text-white hover:bg-white/10 hover:text-white" title="放大" onClick={() => zoom(0.8)}><Plus className="size-4" /></Button>
        <Button variant="ghost" size="icon" className="size-8 text-white hover:bg-white/10 hover:text-white" title="缩小" onClick={() => zoom(1.25)}><Minus className="size-4" /></Button>
        <Button variant="ghost" size="icon" className="size-8 text-white hover:bg-white/10 hover:text-white" title="重置视图" onClick={resetView}><RotateCcw className="size-4" /></Button>
        <Button variant="ghost" size="icon" className="size-8 text-white hover:bg-white/10 hover:text-white" title={isFullscreen ? "退出全屏" : "全屏"} onClick={toggleFullscreen}>{isFullscreen ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}</Button>
      </div>
    </div>
  );
}
