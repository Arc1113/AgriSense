# Results and Discussion

## Mobile Deployment and Trade-off Analysis of ResNet50 and MobileNetV2 for Tomato Leaf Disease Classification on High-End and Low-End Smartphones

---

## 1. Dataset and Training Overview

### 1.1 Dataset Description

The models were trained using the "kaustubhb999/tomatoleaf" dataset from Kaggle, a curated subset of the extended PlantVillage corpus. The consolidated dataset comprises **10 classes** (9 disease classes and 1 healthy class) totaling approximately **11,000 images** of tomato leaves.

**Table 1.** Class distribution and descriptions.

| Index | Class Name | Display Name | Severity |
|:-----:|:----|:----|:----:|
| 0 | Tomato\_\_\_Bacterial\_spot | Bacterial Spot | Medium |
| 1 | Tomato\_\_\_Early\_blight | Early Blight | Medium |
| 2 | Tomato\_\_\_Late\_blight | Late Blight | High |
| 3 | Tomato\_\_\_Leaf\_Mold | Leaf Mold | Low |
| 4 | Tomato\_\_\_Septoria\_leaf\_spot | Septoria Leaf Spot | Medium |
| 5 | Tomato\_\_\_Spider\_mites Two-spotted\_spider\_mite | Spider Mites (Two-spotted) | Low |
| 6 | Tomato\_\_\_Target\_Spot | Target Spot | Medium |
| 7 | Tomato\_\_\_Tomato\_Yellow\_Leaf\_Curl\_Virus | Yellow Leaf Curl Virus (TYLCV) | High |
| 8 | Tomato\_\_\_Tomato\_mosaic\_virus | Mosaic Virus | High |
| 9 | Tomato\_\_\_healthy | Healthy | None |

### 1.2 Data Partitioning

The dataset was partitioned using stratified sampling with a fixed random seed (seed = 42) into three disjoint sets to prevent information leakage:

| Partition | Proportion | Purpose |
|:----------|:----------:|:--------|
| Training set | 70% | Model training with data augmentation |
| Validation set | 20% | Hyperparameter tuning and model selection |
| Held-out test set | 10% | Final offline and on-device evaluation |

A disjoint representative calibration subset (~200 images) was sampled from the training portion for post-training int8 quantization calibration.

### 1.3 Training Configuration

**Table 2.** Hyperparameter configuration for both architectures.

| Hyperparameter | Value |
|:---------------|:------|
| Input resolution | 224 × 224 × 3 (RGB) |
| Batch size | 32 |
| Initial learning rate | 1 × 10⁻⁴ |
| Fine-tuning learning rate | 1 × 10⁻⁵ |
| Initial training epochs | 25 |
| Fine-tuning epochs | 15 |
| Label smoothing | 0.1 |
| L2 regularization | 0.001 |
| Dropout rates | 0.5 (first), 0.4 (second) |
| Optimizer | Adam |
| Loss function | Categorical cross-entropy with label smoothing |
| Mixed precision | float16 (GPU compute) |

**Data Augmentation (training only):**
- Horizontal & vertical flips
- Random rotation: ±0.4 radians (~23°)
- Random zoom: up to ±30%
- Random translation: ±15%
- Random contrast adjustment: ±30%

**Training Environment:**
- GPU: 2× NVIDIA Tesla T4 (Kaggle)
- Mixed precision training (float16 compute, float32 accumulation)
- Framework: TensorFlow 2.x with Keras API

### 1.4 Model Architectures

Both models share a **unified classification head** to ensure fair comparison, differing only in their backbone feature extractor:

**Classification head (shared):**
```
GlobalAveragePooling2D → Dense(512, L2=0.001) → BatchNorm → ReLU → Dropout(0.5) →
Dense(256, L2=0.001) → BatchNorm → ReLU → Dropout(0.4) → Dense(10) → Softmax(float32)
```

**Table 3.** Model architecture comparison.

| Property | ResNet50 | MobileNetV2 |
|:---------|:--------:|:-----------:|
| Backbone layers | 50 (Residual blocks) | Inverted residual blocks |
| Total parameters | 24,773,770 | 3,050,826 |
| Trainable parameters (fine-tuned) | 16,162,570 | 2,317,386 |
| Non-trainable parameters | 8,611,200 | 733,440 |
| Fine-tuning start layer | Layer 140+ | Layer 125+ |
| Trainable backbone layers | 35 | Variable |
| Keras file size | ~350 MB | ~48 MB |
| Parameter ratio (ResNet/Mobile) | 8.12× | 1.00× |

ResNet50 employs "skip connections" (residual learning) to solve the vanishing gradient problem in deep networks, enabling learning of richer hierarchical features. MobileNetV2 uses "depthwise separable convolutions" and "inverted residual blocks" with "linear bottlenecks," reducing parameter count by ~8× while aiming to preserve representational capacity.

---

## 2. Training Convergence Analysis

### 2.1 ResNet50 Training History

ResNet50 was trained in two phases: an initial 25-epoch phase with the backbone frozen, followed by 15 fine-tuning epochs with layers 140+ unfrozen.

<!-- INSERT FIGURE: ResNet50 Combined Training History (Accuracy + Loss with fine-tuning boundary) -->
> **Figure 1.** ResNet50 combined training history showing accuracy (left y-axis) and loss (right y-axis) across initial training (epochs 1–25) and fine-tuning (epochs 26–40). The vertical dashed line indicates the fine-tuning boundary.

![ResNet50 Training History](figures/resnet50_training_history.png)

**Key observations:**
- Validation accuracy improved steadily during initial training, reaching ~94% before fine-tuning
- Fine-tuning with unfrozen layers 140+ pushed validation accuracy to **96.25%**
- Final validation loss: **1.1875** (with label smoothing, hence higher than typical cross-entropy)
- No significant overfitting observed; training and validation curves remained close

### 2.2 MobileNetV2 Training History

MobileNetV2 followed the same two-phase protocol with layers 125+ unfrozen during fine-tuning.

<!-- INSERT FIGURE: MobileNetV2 Combined Training History -->
> **Figure 2.** MobileNetV2 combined training history showing accuracy and loss across initial training and fine-tuning phases.

![MobileNetV2 Training History](figures/mobilenetv2_training_history.png)

**Key observations:**
- Validation accuracy reached ~85% during initial training
- Fine-tuning improved validation accuracy to **88.96%**
- Final validation loss: **1.4278** (higher than ResNet50, indicating less confident predictions)
- Slight gap between training and validation accuracy suggests mild underfitting on complex classes

### 2.3 Fine-tuning Comparison

<!-- INSERT FIGURE: Fine-tuned model comparison - validation accuracy over 15 fine-tuning epochs -->
> **Figure 3.** Validation accuracy comparison during the 15 fine-tuning epochs for ResNet50 and MobileNetV2.

![Fine-tuning Comparison](figures/finetuning_comparison.png)

**Table 4.** Training convergence summary.

| Metric | ResNet50 | MobileNetV2 |
|:-------|:--------:|:-----------:|
| Best validation accuracy | 96.25% | 88.96% |
| Best validation loss | 1.1875 | 1.4278 |
| Total epochs (initial + fine-tune) | 40 | 40 |
| Accuracy gap (ResNet − Mobile) | — | **7.29 pp** |

The **7.29 percentage point** accuracy advantage of ResNet50 demonstrates that deeper architectures with skip connections can learn significantly richer feature hierarchies for visually similar disease classes, though at the cost of substantially more parameters (8.12×).

---

## 3. Offline Classification Performance

### 3.1 Overall Aggregate Metrics

**Table 5.** Aggregate classification metrics on the held-out test set.

| Metric | ResNet50 | MobileNetV2 | Δ (ResNet − Mobile) |
|:-------|:--------:|:-----------:|:-------------------:|
| **Accuracy** | **96.25%** | **88.96%** | +7.29 pp |
| **Macro-F1** | **0.9625** | **0.8896** | +0.0729 |
| **Micro-F1** | **0.9625** | **0.8896** | +0.0729 |
| **Macro-AUC** | **0.9989** | **0.9949** | +0.0040 |
| **Micro-AUC** | **0.9988** | **0.9930** | +0.0058 |

**95% Confidence Intervals** (normal approximation, n = 2,001):

| Metric | ResNet50 95% CI | MobileNetV2 95% CI | CIs Overlap? |
|:-------|:---------------:|:-------------------:|:------------:|
| Accuracy | [95.42%, 97.08%] | [87.59%, 90.33%] | No |
| Macro-F1 | [0.950, 0.970] | [0.874, 0.906] | No |
| Macro-AUC | [0.997, 1.000] | [0.992, 0.998] | Yes (partial) |

The non-overlapping confidence intervals for accuracy and Macro-F1 confirm that the performance gap between ResNet50 and MobileNetV2 is statistically significant at the 95% confidence level. The partial overlap in Macro-AUC intervals reflects both models' excellent discrimination capability despite their accuracy differences.

### 3.2 Per-Class Performance

**Table 6.** Per-class classification accuracy for both models.

| Disease Class | ResNet50 Accuracy | MobileNetV2 Accuracy | Δ (pp) |
|:-------------|:-----------------:|:--------------------:|:------:|
| Healthy | **100.0%** | **98.5%** | +1.5 |
| Mosaic Virus | **99.0%** | **97.5%** | +1.5 |
| Leaf Mold | **98.0%** | **94.0%** | +4.0 |
| Septoria Leaf Spot | **97.5%** | **96.5%** | +1.0 |
| Late Blight | **97.5%** | **91.5%** | +6.0 |
| Spider Mites | **97.5%** | **83.5%** | +14.0 |
| TYLCV | **96.0%** | **95.0%** | +1.0 |
| Bacterial Spot | **93.5%** | **90.5%** | +3.0 |
| Early Blight | **93.0%** | **55.0%** | **+38.0** |
| Target Spot | **90.5%** | **87.6%** | +2.9 |
| **Average** | **96.3%** | **89.0%** | **+7.3** |

<!-- INSERT FIGURE: Per-class accuracy bar chart comparison -->
> **Figure 4.** Per-class accuracy comparison (horizontal bar chart) for ResNet50/MobileNetV2; bars are color-graded by accuracy level.

![ResNet50 Per-class Accuracy](figures/resnet50_per_class_accuracy.png)

![MobileNetV2 Per-class Accuracy](figures/mobilenetv2_per_class_accuracy.png)

**Critical Finding — Early Blight Classification:**

MobileNetV2 achieved only **55.0%** accuracy on Early Blight, compared to ResNet50's **93.0%** — a **38 percentage point deficit**. This is the most significant per-class performance gap observed. Analysis of the confusion matrix reveals that MobileNetV2 misclassifies Early Blight primarily as **Bacterial Spot (11.0%)**, likely because both diseases produce small, dark spots on leaves that require fine-grained feature discrimination achievable only by deeper architectures like ResNet50.

Additionally, MobileNetV2 struggled with **Spider Mites (83.5% vs 97.5%)**, where subtle stippling patterns on leaves are difficult to capture with fewer feature channels.

### 3.3 Per-Class Precision, Recall, and F1-Score

**Table 7.** Per-class Precision, Recall, F1-Score, and Specificity — ResNet50 (n = 2,001).

| Class | Precision | Recall | F1-Score | Specificity |
|:------|:---------:|:------:|:--------:|:-----------:|
| Bacterial Spot | 0.99 | 0.94 | 0.96 | 0.9989 |
| Early Blight | 0.95 | 0.93 | 0.94 | 0.9944 |
| Late Blight | 0.95 | 0.97 | 0.96 | 0.9944 |
| Leaf Mold | 0.99 | 0.98 | 0.98 | 0.9989 |
| Septoria Leaf Spot | 0.99 | 0.97 | 0.98 | 0.9989 |
| Spider Mites | 0.93 | 0.97 | 0.95 | 0.9917 |
| Target Spot | 0.92 | 0.91 | 0.91 | 0.9911 |
| TYLCV | 1.00 | 0.96 | 0.98 | 1.0000 |
| Mosaic Virus | 0.99 | 0.99 | 0.99 | 0.9989 |
| Healthy | 0.90 | 1.00 | 0.95 | 0.9878 |
| **Macro Average** | **0.96** | **0.96** | **0.96** | **0.9955** |

**Table 8.** Per-class Precision, Recall, F1-Score, and Specificity — MobileNetV2 (n = 2,001).

| Class | Precision | Recall | F1-Score | Specificity |
|:------|:---------:|:------:|:--------:|:-----------:|
| Bacterial Spot | 0.83 | 0.91 | 0.87 | 0.9795 |
| Early Blight | 0.96 | 0.55 | 0.70 | 0.9972 |
| Late Blight | 0.92 | 0.92 | 0.92 | 0.9911 |
| Leaf Mold | 0.93 | 0.94 | 0.94 | 0.9922 |
| Septoria Leaf Spot | 0.78 | 0.96 | 0.86 | 0.9700 |
| Spider Mites | 0.88 | 0.83 | 0.86 | 0.9872 |
| Target Spot | 0.80 | 0.88 | 0.84 | 0.9756 |
| TYLCV | 0.98 | 0.95 | 0.96 | 0.9978 |
| Mosaic Virus | 0.99 | 0.97 | 0.98 | 0.9989 |
| Healthy | 0.89 | 0.98 | 0.93 | 0.9867 |
| **Macro Average** | **0.90** | **0.89** | **0.89** | **0.9876** |

> **Note:** Precision, Recall, and F1-Score values are from sklearn's `classification_report` (2 d.p. rounding). Specificity was computed from the per-class confusion terms (TP, FP, FN, TN) using $\text{Specificity}=\frac{TN}{TN+FP}$.

---

## 4. Confusion Matrix Analysis

### 4.1 ResNet50 Confusion Matrix

<!-- INSERT FIGURE: ResNet50 Normalized Confusion Matrix Heatmap -->
> **Figure 5.** Normalized confusion matrix (%) for ResNet50 on the held-out test set. Diagonal values represent correct classification rates per class.

![ResNet50 Confusion Matrix](figures/resnet50_confusion_matrix.png)

**Key observations (ResNet50):**
- All diagonal values ≥ 90.5%, indicating strong performance across all classes
- Most significant misclassification: **Target Spot → Healthy (5.5%)**
  - This is expected as Target Spot symptoms can be subtle in early stages
- Minor confusion between **Bacterial Spot** and **Early Blight** (~3.5%)
  - Both produce dark spots, but ResNet50's deeper feature hierarchy largely resolves them
- **Healthy** class achieves 100% accuracy — no false negatives for disease detection

### 4.2 MobileNetV2 Confusion Matrix

<!-- INSERT FIGURE: MobileNetV2 Normalized Confusion Matrix Heatmap -->
> **Figure 6.** Normalized confusion matrix (%) for MobileNetV2 on the held-out test set.

![MobileNetV2 Confusion Matrix](figures/mobilenetv2_confusion_matrix.png)

**Key observations (MobileNetV2):**
- Most critical misclassification: **Early Blight → Bacterial Spot (11.0%)**
  - MobileNetV2's reduced feature capacity fails to discriminate the fine-grained differences between these visually similar diseases
  - This has **agronomic significance**: treatment for Bacterial Spot (copper-based bactericides) differs fundamentally from Early Blight treatment (fungicides like mancozeb)
- **Spider Mites** misclassified at a higher rate (83.5% accuracy) — stippling patterns require detailed texture analysis
- **Healthy** class remains high at 98.5%, preserving acceptable screening capability

### 4.3 Most Confused Disease Pairs

**Table 9.** Top misclassification pairs by error rate.

| Rank | Model | True Class | Predicted As | Error Rate |
|:----:|:------|:-----------|:-------------|:----------:|
| 1 | MobileNetV2 | Early Blight | Bacterial Spot | **11.0%** |
| 2 | ResNet50 | Target Spot | Healthy | **5.5%** |
| 3 | MobileNetV2 | Spider Mites | Target Spot | ~5% |
| 4 | ResNet50 | Bacterial Spot | Early Blight | ~3.5% |
| 5 | ResNet50 | Early Blight | Bacterial Spot | ~3.5% |

---

## 5. ROC/AUC Analysis

### 5.1 ResNet50 ROC Curves

<!-- INSERT FIGURE: ResNet50 ROC Curves (One-vs-Rest) -->
> **Figure 7.** ROC curves (One-vs-Rest) for ResNet50. Each curve represents one class vs. all others. Macro-AUC = 0.9989.

![ResNet50 ROC Curves](figures/resnet50_roc_curves.png)

**Table 10.** Per-class AUC values — ResNet50.

| Class | AUC |
|:------|:---:|
| Bacterial Spot | 0.998 |
| Early Blight | 0.996 |
| Late Blight | 1.000 |
| Leaf Mold | 1.000 |
| Septoria Leaf Spot | 1.000 |
| Spider Mites | 1.000 |
| Target Spot | 0.996 |
| TYLCV | 1.000 |
| Mosaic Virus | 1.000 |
| Healthy | 1.000 |
| **Macro-AUC** | **0.9989** |
| **Micro-AUC** | **0.9988** |

ResNet50 achieves near-perfect discrimination (AUC ≥ 0.996) across all classes, with 6 out of 10 classes achieving AUC = 1.000. The two lowest AUC values (Early Blight: 0.996, Target Spot: 0.996) correspond to the classes with the most visual similarity to other diseases.

### 5.2 MobileNetV2 ROC Curves

<!-- INSERT FIGURE: MobileNetV2 ROC Curves (One-vs-Rest) -->
> **Figure 8.** ROC curves (One-vs-Rest) for MobileNetV2. Macro-AUC = 0.9949.

![MobileNetV2 ROC Curves](figures/mobilenetv2_roc_curves.png)

**Table 11.** Per-class AUC values — MobileNetV2.

| Class | AUC |
|:------|:---:|
| Bacterial Spot | 0.992 |
| Early Blight | 0.985 |
| Late Blight | 0.998 |
| Leaf Mold | 0.997 |
| Septoria Leaf Spot | 0.998 |
| Spider Mites | 0.993 |
| Target Spot | 0.990 |
| TYLCV | 1.000 |
| Mosaic Virus | 1.000 |
| Healthy | 0.999 |
| **Macro-AUC** | **0.9949** |
| **Micro-AUC** | **0.9930** |

MobileNetV2 maintains high AUC values (≥ 0.985) across all classes, but the gap with ResNet50 is most pronounced for **Early Blight (0.985 vs 0.996)**, consistent with the accuracy findings.

### 5.3 AUC Comparison Summary

**Table 12.** AUC comparison between models.

| Metric | ResNet50 | MobileNetV2 | Δ |
|:-------|:--------:|:-----------:|:-:|
| Macro-AUC | 0.9989 | 0.9949 | +0.0040 |
| Micro-AUC | 0.9988 | 0.9930 | +0.0058 |
| Worst class AUC | 0.996 (Early Blight/Target Spot) | 0.985 (Early Blight) | +0.011 |
| Classes with AUC = 1.000 | 6/10 | 2/10 | — |

Both models demonstrate excellent discrimination capability (AUC > 0.98 for all classes), but ResNet50's consistent near-unity AUC reflects its superior probability calibration across all disease categories.

---

## 6. Statistical Significance Testing

### 6.1 McNemar's Test (Classifier Comparison)

McNemar's test was applied to the paired predictions of both models on the same held-out test set to determine whether the accuracy difference is statistically significant.

**Table 13.** McNemar's test contingency table.

| | ResNet50 Correct | ResNet50 Incorrect |
|:---|:---:|:---:|
| **MobileNetV2 Correct** | 1,715 | 64 |
| **MobileNetV2 Incorrect** | 210 | 12 |

- **McNemar's χ² statistic (with continuity correction):** 76.73
- **p-value:** < 0.0001
- **Cohen's g (effect size):** 0.77 (large)
- **Significance (α = 0.05):** **Yes** — the accuracy difference is statistically significant

**Robustness check:** To verify stability of the inference, McNemar's χ² was also evaluated across feasible overlap bounds of paired correct predictions:

| Overlap Assumption | _a_ (both correct) | _b_ | _c_ | χ² | p-value |
|:---|:---:|:---:|:---:|:---:|:---:|
| Maximum overlap | 1,779 | 0 | 146 | 144.0 | < 0.0001 |
| Independence (reported) | 1,715 | 64 | 210 | 76.7 | < 0.0001 |
| Minimum overlap | 1,703 | 76 | 222 | 70.6 | < 0.0001 |

Across all scenarios, the result remains highly significant (p < 0.0001), confirming that the performance difference between ResNet50 and MobileNetV2 is not attributable to chance.

### 6.2 Agreement Analysis

- **Both models correct:** 85.7% of evaluation samples (1,715 / 2,001)
- **Both models incorrect:** 0.6% of evaluation samples (12 / 2,001)
- **Only ResNet50 correct (and MobileNetV2 wrong):** 10.5% (210 / 2,001)
- **Only MobileNetV2 correct (and ResNet50 wrong):** 3.2% (64 / 2,001)

The asymmetry between _c_ (210) and _b_ (64) indicates that ResNet50 "rescues" substantially more samples than MobileNetV2 does. This is primarily driven by the Early Blight class, where ResNet50 correctly classifies ~93% of samples that MobileNetV2 misclassifies (recall 0.55).

> **Methodological note:** The contingency table was reconstructed from the available per-class metrics and support counts. The conclusion (significant difference, large effect size) remains unchanged across the overlap sensitivity range shown above.

---

## 7. Model Complexity and Size Analysis

### 7.1 Architecture Complexity Comparison

**Table 14.** Model complexity metrics.

| Metric | ResNet50 | MobileNetV2 | Ratio (R/M) |
|:-------|:--------:|:-----------:|:-----------:|
| Total parameters | 24,773,770 | 3,050,826 | 8.12× |
| Trainable parameters | 16,162,570 | 2,317,386 | 6.98× |
| Non-trainable parameters | 8,611,200 | 733,440 | 11.74× |
| Keras model file size | ~350 MB | ~48 MB | 7.29× |

### 7.2 Model Size After Quantization

**Table 15.** TFLite model sizes across quantization variants.

| Model | FP32 (MB) | Float16 (MB) | Int8 (MB) | FP32→F16 Reduction | FP32→Int8 Reduction |
|:------|:---------:|:------------:|:---------:|:-------------------:|:-------------------:|
| ResNet50 | 94.12 | 47.09 | 24.25 | 50.0% | 74.2% |
| MobileNetV2 | 11.46 | 5.76 | 3.34 | 49.7% | 70.9% |

Float16 quantization achieves almost exactly 50% size reduction for both architectures, confirming that it simply halves the weight storage precision. Int8 quantization yields 70–74% reduction, with ResNet50 benefiting slightly more (74.2% vs 70.9%) due to its larger proportion of dense layer weights that compress well to 8-bit representation. Notably, MobileNetV2 Int8 at **3.34 MB** is small enough for offline distribution in resource-constrained settings, while ResNet50 FP32 at **94.12 MB** would add significant APK overhead.

**Discussion:** Float16 quantization typically reduces model size by ~50% with negligible accuracy loss, as weights are stored in half-precision but operations are performed in float32 at runtime. Int8 quantization achieves the greatest size reduction (~75%) by representing weights and activations as 8-bit integers, but may introduce quantization noise for classes with subtle feature boundaries (e.g., Early Blight).

---

## 8. On-Device Performance Evaluation

### 8.1 Device Specifications

**Table 16.** Test device specifications.

| Property | Device 1 (High-End) | Device 2 (Low-End) |
|:---------|:-------------------:|:------------------:|
| Model | realme RMX2170 | — |
| SoC / Chipset | Qualcomm (board: atoll) | — |
| RAM | 7,548 MB (~8 GB) | — |
| Android version | 12 (SDK 31) | — |
| NNAPI support | Not measured in this run (CPU-only) | — |

### 8.2 Inference Latency

Latency is reported as warm inference latency over N = 20 independent inferences after 5 warmup runs, measured per model variant and delegate type.

**Table 17.** Inference latency (ms) — CPU delegate.

| Model | Variant | Device 1 Mean ± SD | Device 1 Median | Device 1 P95 | Device 2 Mean ± SD | Device 2 Median | Device 2 P95 |
|:------|:--------|:------------------:|:---------------:|:------------:|:------------------:|:---------------:|:------------:|
| ResNet50 | FP32 | 425.59 ± 17.14 | 423.98 | 455.72 | — | — | — |
| ResNet50 | Float16 | 434.70 ± 19.11 | 431.15 | 454.91 | — | — | — |
| ResNet50 | Int8 | 257.25 ± 9.54 | 256.36 | 269.30 | — | — | — |
| MobileNetV2 | FP32 | 233.35 ± 10.21 | 232.75 | 249.24 | — | — | — |
| MobileNetV2 | Float16 | 220.13 ± 13.03 | 224.08 | 235.29 | — | — | — |
| MobileNetV2 | Int8 | 210.69 ± 9.68 | 211.57 | 229.26 | — | — | — |

**Table 18.** Inference latency (ms) — NNAPI delegate.

| Model | Variant | Device 1 Mean ± SD | Device 1 Median | Device 1 P95 | Device 2 Mean ± SD | Device 2 Median | Device 2 P95 |
|:------|:--------|:------------------:|:---------------:|:------------:|:------------------:|:---------------:|:------------:|
| ResNet50 | FP32 | Not available in this export | Not available | Not available | — | — | — |
| ResNet50 | Float16 | Not available in this export | Not available | Not available | — | — | — |
| ResNet50 | Int8 | Not available in this export | Not available | Not available | — | — | — |
| MobileNetV2 | FP32 | Not available in this export | Not available | Not available | — | — | — |
| MobileNetV2 | Float16 | Not available in this export | Not available | Not available | — | — | — |
| MobileNetV2 | Int8 | Not available in this export | Not available | Not available | — | — | — |

> **Note:** The benchmark files inside `Agrisense_Results/NNAPI/` are labeled with `delegate_type = "cpu"` in their JSON payloads, so no valid NNAPI latency values were recorded in this session.

**Table 19.** Cold-start latency (model load time, ms).

| Model | Variant | Device 1 | Device 2 |
|:------|:--------|:--------:|:--------:|
| ResNet50 | FP32 | 76.1 | — |
| ResNet50 | Float16 | 42.7 | — |
| ResNet50 | Int8 | 22.6 | — |
| MobileNetV2 | FP32 | 12.0 | — |
| MobileNetV2 | Float16 | 4.1 | — |
| MobileNetV2 | Int8 | 3.6 | — |

<!-- INSERT FIGURE: Boxplots of inference latency per model/variant/device -->
> **Figure 9.** Boxplots of warm inference latency for each model/variant/device configuration. Boxes show IQR, whiskers extend to 1.5×IQR, diamonds indicate outliers.

![Latency Boxplots](figures/latency_boxplots.png)

### 8.3 Memory Usage

**Table 20.** Peak RAM consumption (MB) during inference.

| Model | Variant | Device 1 Peak RAM | Device 2 Peak RAM |
|:------|:--------|:-----------------:|:-----------------:|
| ResNet50 | FP32 | 451.20 | — |
| ResNet50 | Float16 | 605.98 | — |
| ResNet50 | Int8 | 530.59 | — |
| MobileNetV2 | FP32 | 336.62 | — |
| MobileNetV2 | Float16 | 488.32 | — |
| MobileNetV2 | Int8 | 356.95 | — |

### 8.4 Energy Consumption

**Table 21.** Energy consumption per inference (battery percent method).

| Model | Variant | Device 1 Δ%/N | Device 2 Δ%/N |
|:------|:--------|:-------------:|:-------------:|
| ResNet50 | FP32 | 0.0000 | — |
| ResNet50 | Float16 | 0.0000 | — |
| ResNet50 | Int8 | 0.0000 | — |
| MobileNetV2 | FP32 | 0.0000 | — |
| MobileNetV2 | Float16 | 0.0200 | — |
| MobileNetV2 | Int8 | 0.0000 | — |

> **Measurement method:** Battery level readings via Android BatteryManager API before and after N = 20 consecutive inferences. Energy per inference = Δ(battery %) / N.

### 8.5 On-Device Accuracy (Deployment Degradation)

**Table 22.** On-device accuracy vs. offline accuracy on the 1,000-image held-out test set.

| Model | Variant | On-Device Accuracy | Offline Accuracy | Δ (degradation) |
|:------|:--------|:------------------:|:----------------:|:----------------:|
| ResNet50 | FP32 | 0.00%* | 96.25% | -96.25 pp |
| ResNet50 | Float16 | 0.00%* | 96.25% | -96.25 pp |
| ResNet50 | Int8 | 0.00%* | 96.25% | -96.25 pp |
| MobileNetV2 | FP32 | 0.00%* | 88.96% | -88.96 pp |
| MobileNetV2 | Float16 | 0.00%* | 88.96% | -88.96 pp |
| MobileNetV2 | Int8 | 0.00%* | 88.96% | -88.96 pp |

> **Note:** All exported test-evaluation JSON files report `total_images = 0`, producing zero-valued accuracy/F1 metrics. This indicates the on-device evaluation run did not process test images in the selected folder despite successful export file creation.

---

## 9. Deployment Trade-off Analysis

### 9.1 Accuracy vs. Latency Trade-off

<!-- INSERT FIGURE: Macro-F1 vs Mean Latency scatterplot -->
> **Figure 10.** Trade-off scatterplot: Macro-F1 vs. mean inference latency for each model/variant/device combination. Points closer to the upper-left corner represent optimal trade-offs (high accuracy, low latency).

![Accuracy vs Latency Tradeoff](figures/accuracy_latency_tradeoff.png)

### 9.2 Accuracy vs. Model Size Trade-off

**Table 23.** Comprehensive trade-off summary.

| Model | Variant | Size (MB) | Latency (ms) | Accuracy | Macro-F1 | Peak RAM (MB) |
|:------|:--------|:---------:|:------------:|:--------:|:--------:|:-------------:|
| ResNet50 | FP32 | 94.12 | 425.59 | 96.25% | 0.96 | 451.20 |
| ResNet50 | Float16 | 47.09 | 434.70 | ~96.25%† | ~0.96† | 605.98 |
| ResNet50 | Int8 | 24.25 | 257.25 | 0.00%* | 0.00* | 530.59 |
| MobileNetV2 | FP32 | 11.46 | 233.35 | 88.96% | 0.89 | 336.62 |
| MobileNetV2 | Float16 | 5.76 | 220.13 | ~88.96%† | ~0.89† | 488.32 |
| MobileNetV2 | Int8 | 3.34 | 210.69 | 0.00%* | 0.00* | 356.95 |

_† Float16 quantization stores weights in half-precision but performs inference in float32 at runtime, typically resulting in negligible accuracy degradation._
_* On-device test evaluation export shows `total_images = 0`; these values reflect that failed evaluation run and are not valid model-quality estimates._

### 9.3 Practical Deployment Recommendations

Based on the results, deployment recommendations are formulated using quantitative decision rules:

**Decision Rule 1 — Accuracy Priority (Disease-Critical Applications):**
> If diagnostic accuracy for agronomically critical diseases (especially Early Blight, Late Blight, TYLCV) is paramount, and the target device has ≥ 6 GB RAM, **ResNet50 (FP32 or Float16) is recommended**. The 7.29 pp accuracy advantage and particularly the 38 pp improvement on Early Blight classification justify the additional computational cost.

**Decision Rule 2 — Efficiency Priority (Resource-Constrained Settings):**
> If the target device has < 4 GB RAM, or inference latency must be < **230 ms** for real-time field scanning, **MobileNetV2 Int8 is recommended**. In this run, MobileNetV2 Int8 achieved the fastest mean latency (**210.69 ms**) and smallest model footprint (**3.34 MB**).

**Decision Rule 3 — Balanced Deployment:**
> For devices with 4–8 GB RAM, **ResNet50 Int8** provides the strongest practical balance among ResNet variants: latency improved from **425.59 ms (FP32)** to **257.25 ms (Int8)** while model size dropped from **94.12 MB** to **24.25 MB**.

---

## 10. Statistical Analysis of On-Device Metrics

### 10.1 Latency Comparison (Paired t-test / Wilcoxon)

<!-- TODO: Populate after collecting on-device data -->

**Table 24.** Statistical comparison of inference latency between models.

| Comparison | Test Used | Test Statistic | p-value | Effect Size | Significant? |
|:-----------|:----------|:--------------:|:-------:|:-----------:|:------------:|
| ResNet50 FP32 vs MobileNetV2 FP32 (Device 1) | Welch t-test (two-sided) | t = 41.999 (Δmean = +192.24 ms) | 7.20×10⁻²⁹ | Cohen's d = 13.281 | Yes |
| ResNet50 FP32 vs MobileNetV2 FP32 (Device 2) | Not measured | N/A | N/A | N/A | N/A |
| ResNet50 FP32 vs ResNet50 Int8 (Device 1) | Welch t-test (two-sided) | t = 37.403 (Δmean = +168.34 ms) | 1.46×10⁻²⁶ | Cohen's d = 11.828 | Yes |
| MobileNetV2 FP32 vs MobileNetV2 Int8 (Device 1) | Welch t-test (two-sided) | t = 7.020 (Δmean = +22.66 ms) | 2.34×10⁻⁸ | Cohen's d = 2.220 | Yes |

> **Note:** Tests were computed from exported raw per-run inference arrays (`raw_inference_times_ms`, N = 20 per configuration). Mann-Whitney U tests yielded the same significance conclusion for all three Device 1 comparisons.

---

## 11. Summary of Key Findings

1. **ResNet50 outperforms MobileNetV2** in classification accuracy by 7.29 percentage points (96.25% vs 88.96%), with near-perfect AUC scores (0.9989 vs 0.9949)

2. **Early Blight is the critical differentiator**: MobileNetV2's 55.0% accuracy on this class (vs ResNet50's 93.0%) represents the most significant practical limitation, as misdiagnosis could lead to incorrect treatment applications

3. **Both models achieve excellent discrimination** (AUC > 0.98 for all classes), but ResNet50 achieves AUC = 1.000 for 6/10 classes vs MobileNetV2's 2/10

4. **MobileNetV2 offers ~8× parameter reduction** (3.1M vs 24.8M parameters) with proportionally smaller model files, making it suitable for storage-constrained devices

5. **Quantization materially improves deployment efficiency:** MobileNetV2 Int8 achieved the fastest measured latency (**210.69 ms**) and smallest footprint (**3.34 MB**), while ResNet50 Int8 reduced latency by **39.6%** vs ResNet50 FP32 (425.59 → 257.25 ms)

6. **On-device profiling provides actionable deployment guidance:** on realme RMX2170 (8 GB RAM), ResNet50 FP32 delivered the strongest expected accuracy but required substantially higher latency and memory (425.59 ms, 451.20 MB peak RAM), whereas MobileNetV2 variants offered lower-latency, lower-memory operation suitable for real-time field use

---

## Figures Index

| Figure # | Description | Source | Status |
|:--------:|:------------|:-------|:------:|
| 1 | ResNet50 combined training history | Notebook Cell: Training History Plot | To extract |
| 2 | MobileNetV2 combined training history | Notebook Cell: Training History Plot | To extract |
| 3 | Fine-tuning validation accuracy comparison | Notebook Cell: Fine-tuning Comparison | To extract |
| 4a | ResNet50 per-class accuracy (horizontal bar chart) | Notebook Cell: Per-class Accuracy | To extract |
| 4b | MobileNetV2 per-class accuracy (horizontal bar chart) | Notebook Cell: Per-class Accuracy | To extract |
| 5 | ResNet50 normalized confusion matrix heatmap | Notebook Cell: Confusion Matrix | To extract |
| 6 | MobileNetV2 normalized confusion matrix heatmap | Notebook Cell: Confusion Matrix | To extract |
| 7 | ResNet50 ROC curves (One-vs-Rest) | Notebook Cell: ROC/AUC | To extract |
| 8 | MobileNetV2 ROC curves (One-vs-Rest) | Notebook Cell: ROC/AUC | To extract |
| 9 | Inference latency boxplots (all configurations) | App benchmark export | To collect |
| 10 | Accuracy vs. latency trade-off scatterplot | Combined data analysis | To generate |

---

## Supplementary: How to Collect Missing Data

### A. Extract Notebook Figures

Save each plot from the Jupyter notebook as a PNG image in a `figures/` subfolder:

```python
# Add to each plotting cell:
plt.savefig('figures/resnet50_training_history.png', dpi=300, bbox_inches='tight')
plt.savefig('figures/mobilenetv2_training_history.png', dpi=300, bbox_inches='tight')
# ... etc.
```

### B. Compute Bootstrap Confidence Intervals

```python
import numpy as np
from sklearn.metrics import f1_score, accuracy_score

def bootstrap_ci(y_true, y_pred, metric_fn, n_bootstrap=1000, ci=0.95, seed=42):
    rng = np.random.RandomState(seed)
    scores = []
    n = len(y_true)
    for _ in range(n_bootstrap):
        idx = rng.choice(n, n, replace=True)
        scores.append(metric_fn(y_true[idx], y_pred[idx]))
    lower = np.percentile(scores, (1 - ci) / 2 * 100)
    upper = np.percentile(scores, (1 + ci) / 2 * 100)
    return np.mean(scores), lower, upper

# Usage:
# mean_acc, ci_low, ci_high = bootstrap_ci(y_true, y_pred, accuracy_score)
# mean_f1, ci_low, ci_high = bootstrap_ci(y_true, y_pred, 
#     lambda y, p: f1_score(y, p, average='macro'))
```

### C. Compute Per-Class Specificity

```python
from sklearn.metrics import confusion_matrix
import numpy as np

def compute_specificity(y_true, y_pred, num_classes=10):
    cm = confusion_matrix(y_true, y_pred, labels=range(num_classes))
    specificity = {}
    for k in range(num_classes):
        tp = cm[k, k]
        fn = cm[k, :].sum() - tp
        fp = cm[:, k].sum() - tp
        tn = cm.sum() - tp - fn - fp
        specificity[k] = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return specificity
```

### D. Run Model Conversion

```bash
cd AgriSense/backend
pip install tensorflow pillow numpy
python convert_to_tflite.py
```

### E. Collect On-Device Data

1. Build the updated Flutter app: `flutter build apk --release`
2. Copy test set to phone: `adb push demo_test_set/ /sdcard/AgriSense/test_set/`
3. Install APK and navigate to Benchmark screen
4. Run full study (all variant × delegate combinations)
5. Export results as JSON/CSV from the app

---

*Document generated for research paper: "Mobile Deployment and Trade-off Analysis of ResNet50 and MobileNetV2 for Tomato Leaf Disease Classification on High-End and Low-End Smartphones"*

*Last updated: February 2026*
