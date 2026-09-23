# Stage C.V1K Bragg 视觉原型人工检查

打开 `/apps/bragg-reflector/` 后检查：

## 结构

- [ ] H/L 固定图例与实际层颜色一致；
- [ ] 三个 H/L 周期和终止 H 层能够快速区分；
- [ ] 页面没有把七层误写成四个完整周期；
- [ ] 周期括号没有暗示定量反射贡献。

## 正式偏振对照

- [ ] 498 nm 时显示 TE R=96.38%、TM R=79.16%；
- [ ] 两个数值来自同一当前波长；
- [ ] 切换波长后 TE/TM 对照同步更新；
- [ ] 当前偏振行具有克制但可辨认的强调。

## 阅读与观察

- [ ] “观察模型”释放结构主体区域；
- [ ] “阅读解释”返回相同引导步骤；
- [ ] 模式切换不改变波长、偏振或选中层；
- [ ] Canvas 与 Renderer 始终为 1。

## 语义边界

- [ ] 高反结论仍来自正式 R；
- [ ] 正弦线仍为教学示意；
- [ ] 无光晕、bloom、粒子或定量膜内场暗示；
- [ ] F-P、单层减反和 Tamm 页面没有变化。

## 自动证据

```text
docs/visualization/runtime/stage_cv1k/bragg_reading.png
docs/visualization/runtime/stage_cv1k/bragg_model_focus.png
```

当前状态：`PENDING MANUAL ACCEPTANCE`
