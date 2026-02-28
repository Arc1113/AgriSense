RESARCH TOPIC/TITLE : Mobile Deployment and Trade-off Analysis of ResNet50 and MobileNetV2 for Tomato Leaf Disease Classification on High-End and Low-End Smartphones.
	Description of the Project
	Rationale
Tomatoes (Solanum lycopersicum) are among the most widely cultivated and economically significant vegetable crops worldwide. According to the Food and Agriculture Organization (FAO), global tomato production remains one of the highest among vegetable commodities, reaching approximately 186 million tonnes in recent years [1]. The global tomato market is likewise substantial, valued at over USD 150 billion in 2024 and projected to continue growing in 2025 [2]. Despite its economic importance, the industry remains highly vulnerable to environmental and biological stresses. In 2025, global processed tomato production declined by approximately 12% due to adverse weather conditions and disease pressures in major producing regions [3], highlighting the crop’s sensitivity to climatic and pathogenic factors.
In the Philippines, tomato production provides livelihood to thousands of farmers and contributes significantly to national food security. The Philippine Statistics Authority reported a production value of approximately PHP 1.29 billion in 2024, reflecting its economic relevance [4]. In the Davao Region (Region XI), agriculture remains a major economic sector; however, regional performance reports indicate slight contractions attributed to climatic variability and production challenges [5]. These instabilities have contributed to severe price fluctuations, with tomato retail prices in some markets reaching as high as PHP 220 per kilogram during supply shortages in 2024 [6].
A major driver of supply instability is the prevalence of infectious plant diseases. Pathogens such as Tomato Yellow Leaf Curl Virus (TYLCV), early blight, and bacterial wilt can cause significant yield losses if left unmanaged [7], [8]. Early and accurate diagnosis is therefore critical. However, current diagnostic practices in many rural areas rely primarily on manual visual inspection by agricultural extension workers, a process that is labor-intensive, limited in remote areas, and susceptible to misclassification [9].
Recent advancements in computer vision and deep learning provide promising solutions for automated plant disease detection. Convolutional Neural Networks (CNNs) have demonstrated high classification accuracy for plant disease recognition tasks [9], [13], [14]. Nevertheless, most studies evaluate performance in controlled environments and do not fully address practical deployment in resource-constrained agricultural settings.
A key technological trade-off exists between model complexity and deployability. Deep architectures such as ResNet50 are capable of learning rich hierarchical feature representations and have achieved strong performance in image classification tasks [11]. However, they require substantial computational resources. In contrast, MobileNetV2 is specifically designed for lightweight mobile inference through depthwise separable convolutions and inverted residual blocks, making it suitable for embedded systems [12], [17]. While MobileNetV2 offers efficiency advantages, there remains uncertainty as to whether its reduced complexity compromises its ability to detect subtle or visually similar tomato diseases compared to deeper architectures.
This study addresses this gap by empirically evaluating the trade-off between diagnostic accuracy and computational efficiency. Both ResNet50 and MobileNetV2 will be trained and subsequently deployed on representative high-end and low-end smartphones. By comparing classification performance, inference latency, memory consumption, and energy usage, this research seeks to determine whether MobileNetV2 is sufficient for practical mobile-based disease diagnosis or whether ResNet50 provides significantly superior recognition performance that justifies its higher computational cost.

	Objectives of the Study
	General
To develop and evaluate MobileNetV2 and ResNet50 architectures for tomato leaf disease classification and to analyze the trade-off between diagnostic accuracy and computational efficiency when deployed on high-end and low-end smartphones.
	Specific
	To train and fine-tune MobileNetV2 and ResNet50 using an extended PlantVillage tomato leaf dataset and evaluate their classification performance using Accuracy, Precision, Recall, F1-score, and Confusion Matrix analysis.
	To convert and deploy both trained models to representative high-end and low-end smartphones for on-device inference.
	To compare the models in terms of diagnostic performance and computational efficiency, including inference latency, model size, memory usage, and overall suitability for real-world mobile-based disease detection.
	Proposed Model
The project will utilize Transfer Learning by leveraging models pre-trained on the ImageNet database to ensure robust feature extraction. Two specific architectures will be implemented to evaluate the trade-off between depth and efficiency. The first, ResNet50, is a 50-layer Residual Network that utilizes "skip connections" to solve the vanishing gradient problem in deep networks, serving as the baseline for high-accuracy feature extraction. In contrast, the study will also implement MobileNetV2, a lightweight network designed for mobile and embedded vision applications that employs "inverted residual blocks" and "linear bottlenecks" to significantly reduce parameter count and computational complexity.
 

Figure 1. [16] Resnet50 Model Framework

 

Figure 2. [17] MobileNetV2 Model Framework
	Methodology
Data Gathering
The primary dataset for this study is the “Tomato Disease (multiple sources)” collection hosted on Kaggle, which aggregates and extends the PlantVillage corpus PlantVillage and other public image sources. The consolidated dataset comprises approximately 32,000 images distributed across 11 classes (ten disease classes and one healthy class). To prevent information leakage during model development, the dataset is partitioned using stratified sampling into three disjoint sets: 70% training, 20% validation, and 10% held-out test. The held-out test set is preserved and remains inaccessible during training and hyperparameter tuning; it is used exclusively for final offline and on-device evaluation.
A small, disjoint representative calibration subset (e.g., ~100–300 images) is sampled from the training portion and set aside for use during post-training quantization calibration (int8) to ensure that calibration statistics do not leak test information.

Data Processing
All preprocessing operations are implemented deterministically in the data pipeline so that training, validation and on-device inference are comparable. The main preprocessing steps are as follows:
	Integrity checks and cleaning.
	Automated validation to remove corrupted files, non-image artifacts, and exact duplicates.
	Manual spot checks of ambiguous or low-quality images to confirm label correctness where necessary.
	Image resizing and format.
	All images are resized to 224 × 224 pixels (bilinear interpolation) and stored as three-channel RGB tensors.
	Images are converted to floating point and cached/serialized in an efficient format for reproducible training runs.
	Model-specific normalization.
	Two separate preprocessing pipelines are maintained to match each architecture’s pretraining conventions:
	ResNet50: Caffe-style preprocessing (channel mean subtraction and scaling consistent with ResNet50 pretrained weights).
	MobileNetV2: TensorFlow MobileNet preprocessing (rescaling to the [−1, +1] range).
	These pipelines are applied consistently at training, validation, test, and on-device inference to avoid covariate shifts.
	Data augmentation (training set only).
	To improve generalization and simulate field variability, on-the-fly augmentations are applied only to training examples. Augmentations include:
	Horizontal and vertical flips.
	Random rotations within ±30°.
	Random zooms up to ±30% (with optional random cropping).
	Random brightness and contrast adjustments and optional hue/saturation jitter to simulate varying illumination and sensor characteristics.
	Augmentation parameters are conservatively bounded to avoid producing unrealistic leaf appearances.
	Class imbalance mitigation.
	Class frequencies are analyzed and class weights are computed and supplied to the loss function to penalize misclassification of underrepresented classes. Where imbalance remains extreme, targeted oversampling of minority classes within the training pipeline will be evaluated in combination with weighted loss.
	Representative calibration subset.
	A disjoint representative subset drawn from the training partition is reserved for quantization calibration (int8). This subset is stratified by class to approximate the overall class distribution and is excluded from validation and testing.
	Deterministic pipeline and reproducibility.
	All random operations (data shuffling, augmentation seeds, and sampling) are controlled by fixed random seeds. File lists, dataset splits, and preprocessing code are versioned and checksummed to ensure reproducibility of experiments.

	Evaluation
The evaluation protocol comprises three complementary components: (1) offline evaluation on a held-out test set, (2) on-device performance assessment for mobile deployment, and (3) statistical analysis to determine the significance and practical importance of observed differences. All offline classification metrics are computed on the preserved held-out test set (20% of the dataset). The validation set (10%) is used exclusively for model selection and hyperparameter tuning.
4.1 Offline classification metrics
The principal objective of offline evaluation is to measure per-class diagnostic performance and overall robustness. For each class k(treating it as the positive class in a one-vs-rest formulation) the confusion matrix yields:
	True Positives: 〖"TP" 〗_k
	False Positives: 〖"FP" 〗_k
	False Negatives: 〖"FN" 〗_k
	True Negatives: 〖"TN" 〗_k
From these counts the following metrics are computed per class:
〖"Precision" 〗_k=〖"TP" 〗_k/(〖"TP" 〗_k+〖"FP" 〗_k ) 〖"Recall" 〗_k=〖"TP" 〗_k/(〖"TP" 〗_k+〖"FN" 〗_k )
〖"F1" 〗_k=2×(〖"Precision" 〗_k×〖"Recall" 〗_k)/(〖"Precision" 〗_k+〖"Recall" 〗_k )

Aggregate metrics that summarize multi-class performance include:
	Macro-F1 (unweighted mean of per-class F1):
"Macro-F1"=1/K ∑_(k=1)^K▒〖"F1" 〗_k 

where K=11is the number of classes. Macro-F1 treats all classes equally and is the primary selection metric for this study because it prevents majority-class dominance.
	Micro-F1 (global F1 computed from summed TP/FP/FN across classes):
"Micro-Precision"=(∑_k▒〖"TP" 〗_k )/(∑_k▒( 〖"TP" 〗_k+〖"FP" 〗_k)),"Micro-Recall"=(∑_k▒〖"TP" 〗_k )/(∑_k▒( 〖"TP" 〗_k+〖"FN" 〗_k))
"Micro-F1"=2×("Micro-Precision" ×"Micro-Recall" )/("Micro-Precision" +"Micro-Recall" )

	Accuracy (overall fraction of correct predictions):
"Accuracy"=(∑_k▒〖"TP" 〗_k )/"Total samples" ="Total correct" /"Total samples" 

Additional offline measures include per-class specificity:
〖"Specificity" 〗_k=〖"TN" 〗_k/(〖"TN" 〗_k+〖"FP" 〗_k )

and ROC/AUC (one-vs-rest) computed from model probability outputs to assess discrimination independent of a chosen threshold. Confidence intervals (95%) for all primary metrics will be estimated via bootstrap resampling of the held-out test set (e.g., 1,000 bootstrap samples).
4.2 On-device performance metrics
Because this study is primarily concerned with mobile deployment trade-offs, on-device performance is assessed for each model variant (float32, float16, int8) on representative high-end and low-end smartphones. The on-device measurement protocol records the following:
	Latency (inference time). Two measures are reported: (a) cold-start latency (time from app launch to first inference completion) and (b) warm inference latency. For warm latency, Nindependent inferences are timed and the mean, median and standard deviation are reported:
"Mean latency"=1/N ∑_(i=1)^N▒t_i 

where t_iis the elapsed time for inference i. Typical N=200. Latency is measured for CPU-only runs and, where supported, with hardware delegates (e.g., NNAPI).
	Model binary size:
"Size (MB)"="file_bytes" /1024^2 

	Memory usage: peak RAM (MB) observed during inference (measured with platform profiling tools).
	CPU utilization: average CPU load (%) during inference; when multi-core measurements are available, per-core and aggregate loads are reported.
	Energy consumption: reported using either (a) battery percent method:
"Energy per inference (% battery)"=(Δ(%"battery" ))/N

or (b) mAh method (preferred if external power meter available):
"mAh per inference"=Δ"mAh" /N

All energy measurements explicitly state the measurement method and limitations.
	On-device accuracy: the held-out test set is processed using the exact on-device preprocessing pipeline and converted model; per-class and aggregate classification metrics are computed and the delta between offline and on-device performance is reported to quantify deployment degradation.
Each device × model × variant experiment is repeated (minimum 3 runs) and results are reported as mean ± standard deviation.
4.3 Efficiency and training metrics
Training efficiency metrics recorded for each experiment include:
	Training time (wall clock):
"Training time"=T_"end" -T_"start" 

Reported in hours/minutes and, where relevant, GPU hours.
	Convergence statistics: number of epochs to best validation performance, epoch of best checkpoint, and learning-rate schedule events.
4.4 Statistical analysis and hypothesis testing
To determine whether observed differences are statistically significant and practically meaningful:
	Classifier comparison (paired, per-sample): apply McNemar’s test to the paired predictions of the two models on the same held-out test set. Report the test statistic and p-value; significance is assessed at α=0.05.
	Continuous metrics (latency, memory, energy): use paired t-test when distributions approximate normality or Wilcoxon signed-rank test otherwise. Report effect size measures (e.g., Cohen’s dfor t-tests or rank-biserial correlation for nonparametric tests) to quantify practical significance alongside p-values.
	Multiple comparisons control: where numerous pairwise comparisons are performed (e.g., multiple variants and devices), apply appropriate corrections (e.g., Benjamini–Hochberg false discovery rate) and report adjusted p-values.
4.5 Reporting and visualization
Results will be presented in tabular and graphical form to facilitate interpretation:
	Table 1 (Offline): per-class Precision, Recall, F1, Macro-F1, Micro-F1, Accuracy, and 95% CI.
	Table 2 (On-device): device, model, variant, model size (MB), mean latency (ms ± std), peak RAM (MB), CPU (%), energy per inference (mAh or %), on-device Macro-F1, and delta vs offline.
	Figure 1: confusion matrix heatmap for the selected offline model.
	Figure 2: boxplots of latency per model/variant/device.
	Figure 3: trade-off scatterplot (Macro-F1 vs mean latency) with points for each model/variant/device to visualize practical deployment choices.
	Appendix: complete logs, device make/model/OS versions, measurement scripts, and model checksums for reproducibility.
4.6 Interpretation criteria
Emphasis in interpretation will be placed on Macro-F1 and per-class performance (especially for minority but agronomically important disease classes). Deployment recommendations will consider practical thresholds (for example, whether a small absolute improvement in Macro-F1 justifies a substantial increase in latency, memory, or energy consumption on low-end devices). Quantitative decision rules (e.g., minimum required Macro-F1 gain vs maximum allowable latency multiplier) will be reported to support objective recommendations for real-world deployment.

 
References
[1] Food and Agriculture Organization (FAO), World Food and Agriculture – Statistical Yearbook 2023, FAO, Rome, Italy, 2023. [Online]. Available: https://openknowledge.fao.org.
[2] Research and Markets, Tomatoes Global Market Report 2025, The Business Research Company, London, UK, Jan. 2025. [Online]. Available: https://www.researchandmarkets.com (report summary).
[3] World Processing Tomato Council, “Global processed tomato output down 12% in 2025,” FreshPlaza, Jan. 12, 2026. [Online]. Available: https://www.freshplaza.com.
[4] Philippine Statistics Authority (PSA), “Value of Production in Philippine Agriculture and Fisheries: First Quarter 2024,” PSA, Quezon City, Philippines, Rep., May 2024.
[5] National Economic and Development Authority (NEDA) Region XI, “CY 2024 Davao Regional Development Report,” RDC XI / NEDA XI, Davao Region, Philippines, 2025.
[6] Department of Agriculture (DA), Price Monitoring of Selected High Value Crops in Metro Markets, Agribusiness and Marketing Assistance Service (AMAS), Quezon City, Philippines, Jul. 26, 2024. [Online]. Available: https://www.da.gov.ph/wp-content/uploads/2024/07/Price-Monitoring-July-26-2024.pdf.
[7] Virology and Vaccine Institute of the Philippines (VIP), “Project 6: Development of LAMP-based Detection Kit for Tomato Yellow Leaf Curl Virus — Philippine strains,” DOST-PCAARRD, Los Baños, Philippines, 2023. [Online]. Available: https://ispweb.pcaarrd.dost.gov.ph.
[8] R. Cerdà et al., “Primary and secondary yield losses caused by pests and diseases,” PLOS ONE, 2017.
[9] S. P. Mohanty, D. P. Hughes, and M. Salathé, “Using deep learning for image-based plant disease detection,” Frontiers in Plant Science, vol. 7, p. 1419, 2016. [Online]. Available: https://doi.org/10.3389/fpls.2016.01419.
[10] J. Liu and X. Wang, “Plant disease detection using deep learning and computer vision,” in Proc. IEEE Int. Conf. Comput. Vis., 2021.
[11] K. He, X. Zhang, S. Ren, and J. Sun, “Deep residual learning for image recognition,” in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2016, pp. 770–778.
[12] M. Sandler, A. Howard, M. Zhu, A. Zhmoginov, and L.-C. Chen, “MobileNetV2: Inverted residuals and linear bottlenecks,” in Proc. IEEE Conf. Comput. Vis. Pattern Recognit. (CVPR), 2018, pp. 4510–4520.
[13] K. P. Ferentinos, “Deep learning models for plant disease detection and diagnosis,” Computers and Electronics in Agriculture, vol. 145, pp. 311–318, 2018.
[14] S. Sladojevic, M. Arsenovic, A. Anderla, D. Culibrk, and D. Stefanovic, “Deep neural networks based recognition of plant diseases by leaf image classification,” Computational Intelligence and Neuroscience, vol. 2016, Art. no. 3289801, 2016.
[15] Cookiefinder, “Tomato disease (multiple sources),” Kaggle Dataset, 2024. [Online]. Available: https://www.kaggle.com/datasets/cookiefinder/tomato-disease-multiple-sources.
[16] Z. Tang, M. Li, and X. Wang, “Mapping tea plantations from very high resolution images using OBIA and convolutional neural networks,” Remote Sensing, vol. 12, no. 18, p. 2935, 2020.
[17] M. Akay et al., “Deep learning classification of systemic sclerosis skin using the MobileNetV2 model,” IEEE Open Journal of Engineering in Medicine and Biology, vol. 2, pp. 1–7, 2021.

