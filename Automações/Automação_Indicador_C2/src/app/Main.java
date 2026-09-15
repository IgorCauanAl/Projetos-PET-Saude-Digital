package app;

import extract.PdfBoxExtractor;
import javafx.application.Application;
import javafx.concurrent.Task;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.Alert;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.ListView;
import javafx.scene.control.ProgressIndicator;
import javafx.scene.layout.BorderPane;
import javafx.scene.layout.HBox;
import javafx.scene.layout.StackPane;
import javafx.scene.layout.VBox;
import javafx.stage.FileChooser;
import javafx.stage.Stage;
import loader.ExcelLoader;
import model.Patient;
import transform.PatientTransformer;

import java.awt.Desktop;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

public class Main extends Application {

    private static final Path TEMPLATE_DIRECTORY = Path.of("Planilha");
    private static final Path OUTPUT_DIRECTORY = Path.of("Planilhas dos ACS");

    private final Label fileInfo = new Label("Nenhum arquivo PDF selecionado.");
    private final Button processButton = new Button("Processar Indicadores");
    private final ListView<String> professionalsList = new ListView<>();
    private final Label[] taskLabels = new Label[3];
    private File selectedPdf;
    private VBox uploadView;
    private VBox resultView;
    private StackPane loadingOverlay;

    public static void main(String[] args) {
        launch(args);
    }

    @Override
    public void start(Stage stage) {
        StackPane root = new StackPane(createWindow());
        root.getStyleClass().add("app-root");
        loadingOverlay = createLoadingOverlay();
        root.getChildren().add(loadingOverlay);

        Scene scene = new Scene(root, 750, 520);
        scene.getStylesheets().add(Main.class.getResource("automation-c2.css").toExternalForm());
        stage.setTitle("Automação C2 - Desenvolvimento Infantil");
        stage.setMinWidth(650);
        stage.setMinHeight(460);
        stage.setScene(scene);
        stage.show();
    }

    private BorderPane createWindow() {
        BorderPane window = new BorderPane();
        window.getStyleClass().add("os-window");
        window.setTop(createHeader());

        StackPane body = new StackPane();
        body.getStyleClass().add("app-content");
        uploadView = createUploadView();
        resultView = createResultView();
        resultView.setVisible(false);
        resultView.setManaged(false);
        body.getChildren().addAll(uploadView, resultView);
        window.setCenter(body);
        return window;
    }

    private VBox createHeader() {
        VBox header = new VBox(5);
        header.getStyleClass().add("app-header");
        Label greeting = new Label("Bem-vinda, Gestora(o)!");
        greeting.getStyleClass().add("greeting");
        Label title = new Label("Automação C2 - Desenvolvimento Infantil");
        title.getStyleClass().add("app-title");
        header.getChildren().addAll(greeting, title);
        return header;
    }

    private VBox createUploadView() {
        VBox card = createCard();
        Label description = new Label("Selecione o relatório PDF. O sistema irá ler as informações para a planillha, "
                + "agrupar os pacientes por Agente Comunitário e gerar as planilhas preenchidas.");
        description.setWrapText(true);
        description.setMaxWidth(470);
        description.getStyleClass().add("description");

        Button chooseFile = new Button("Selecionar PDF");
        chooseFile.getStyleClass().add("primary-button");
        chooseFile.setOnAction(event -> choosePdf());
        processButton.getStyleClass().add("highlight-button");
        processButton.setDisable(true);
        processButton.setOnAction(event -> processPdf());

        HBox buttons = new HBox(15, chooseFile, processButton);
        buttons.setAlignment(Pos.CENTER);
        fileInfo.getStyleClass().add("file-info");
        card.getChildren().addAll(description, buttons, fileInfo);
        return card;
    }

    private VBox createResultView() {
        VBox card = createCard();
        Label success = new Label("✓  Planilhas geradas com sucesso!");
        success.getStyleClass().add("result-title");
        Label subtitle = new Label("Agentes Comunitários processados:");
        subtitle.getStyleClass().add("result-subtitle");

        professionalsList.getStyleClass().add("professionals-list");
        professionalsList.setPrefHeight(145);
        professionalsList.setMaxWidth(460);
        professionalsList.setFocusTraversable(true);
        professionalsList.setMouseTransparent(false);

        Button openFolder = new Button("Abrir Pasta com as Planihas");
        openFolder.getStyleClass().add("primary-button");
        openFolder.setOnAction(event -> openOutputFolder());
        Button newFile = new Button("Novo Arquivo");
        newFile.getStyleClass().add("outline-button");
        newFile.setOnAction(event -> resetUpload());
        HBox buttons = new HBox(15, openFolder, newFile);
        buttons.setAlignment(Pos.CENTER);
        card.getChildren().addAll(success, subtitle, professionalsList, buttons);
        return card;
    }

    private VBox createCard() {
        VBox card = new VBox(20);
        card.getStyleClass().add("card");
        card.setAlignment(Pos.CENTER);
        card.setMaxWidth(550);
        card.setPrefWidth(550);
        return card;
    }

    private StackPane createLoadingOverlay() {
        VBox panel = new VBox(14);
        panel.getStyleClass().add("loading-panel");
        panel.setAlignment(Pos.CENTER);
        ProgressIndicator spinner = new ProgressIndicator();
        spinner.getStyleClass().add("spinner");
        spinner.setPrefSize(52, 52);
        Label title = new Label("Processando Relatório");
        title.getStyleClass().add("loading-title");
        panel.getChildren().addAll(spinner, title);

        String[] tasks = {
                "Capturando as informações do PDF ",
                "Aguarde um momento...",
                "Gerando pastas e planilhas por ACS"
        };
        for (int index = 0; index < tasks.length; index++) {
            taskLabels[index] = new Label("○  " + tasks[index]);
            taskLabels[index].getStyleClass().add("task-item");
            panel.getChildren().add(taskLabels[index]);
        }

        StackPane overlay = new StackPane(panel);
        overlay.getStyleClass().add("loading-overlay");
        overlay.setVisible(false);
        overlay.setManaged(false);
        overlay.setMouseTransparent(true);
        return overlay;
    }

    private void choosePdf() {
        FileChooser chooser = new FileChooser();
        chooser.setTitle("Selecionar relatório PDF");
        chooser.getExtensionFilters().add(new FileChooser.ExtensionFilter("Arquivos PDF", "*.pdf"));
        File file = chooser.showOpenDialog(fileInfo.getScene().getWindow());
        if (file != null) {
            selectedPdf = file;
            fileInfo.setText("Arquivo carregado: " + file.getName());
            processButton.setDisable(false);
        }
    }

    private void processPdf() {
        if (selectedPdf == null) {
            return;
        }
        showLoading(true);
        updateTaskState(0);

        Task<List<String>> task = new Task<>() {
            @Override
            protected List<String> call() throws Exception {
                String rawText = new PdfBoxExtractor().extractRawText(selectedPdf);
                if (rawText.isBlank()) {
                    throw new IllegalStateException("O PDF não contém texto para processar.");
                }
                updateMessage("1");
                List<Patient> patients = new PatientTransformer().transform(rawText);
                if (patients.isEmpty()) {
                    throw new IllegalStateException("Nenhum paciente foi encontrado no relatório.");
                }
                updateMessage("2");
                Files.createDirectories(OUTPUT_DIRECTORY);
                new ExcelLoader().generateReports(patients, OUTPUT_DIRECTORY.toFile(),
                        findSpreadsheet(TEMPLATE_DIRECTORY).toString());
                return professionalDirectories(patients);
            }
        };
        task.messageProperty().addListener((observable, previous, current) -> {
            if (!current.isBlank()) {
                updateTaskState(Integer.parseInt(current));
            }
        });
        task.setOnSucceeded(event -> {
            professionalsList.getItems().setAll(task.getValue().stream()
                    .map(name -> "📁  Pasta gerada: " + name).toList());
            showLoading(false);
            uploadView.setVisible(false);
            uploadView.setManaged(false);
            resultView.setVisible(true);
            resultView.setManaged(true);
        });
        task.setOnFailed(event -> {
            showLoading(false);
            processButton.setDisable(false);
            showError("Não foi possível processar o relatório.", rootMessage(task.getException()));
        });
        Thread processingThread = new Thread(task, "c2-pdf-processing");
        processingThread.setDaemon(true);
        processingThread.start();
    }

    private void updateTaskState(int activeTask) {
        for (int index = 0; index < taskLabels.length; index++) {
            Label task = taskLabels[index];
            task.getStyleClass().removeAll("processing", "done");
            String description = task.getText().substring(3);
            if (index < activeTask) {
                task.setText("✓  " + description);
                task.getStyleClass().add("done");
            } else if (index == activeTask) {
                task.setText("◌  " + description);
                task.getStyleClass().add("processing");
            } else {
                task.setText("○  " + description);
            }
        }
    }

    private void showLoading(boolean visible) {
        loadingOverlay.setVisible(visible);
        loadingOverlay.setManaged(visible);
        loadingOverlay.setMouseTransparent(!visible);
        if (visible) {
            loadingOverlay.toFront();
        }
    }

    private List<String> professionalDirectories(List<Patient> patients) {
        Set<String> directories = new LinkedHashSet<>();
        for (Patient patient : patients) {
            String professional = patient.getLinkedProfessional();
            directories.add(professional == null || professional.isBlank()
                    ? "PROFISSIONAL_NAO_INFORMADO"
                    : professional.replaceAll("[^a-zA-Z0-9_ ]", "").trim());
        }
        return new ArrayList<>(directories);
    }

    private void openOutputFolder() {
        try {
            Files.createDirectories(OUTPUT_DIRECTORY);
            if (System.getProperty("os.name").toLowerCase().contains("linux")) {
                new ProcessBuilder("xdg-open", OUTPUT_DIRECTORY.toAbsolutePath().toString()).start();
            } else if (Desktop.isDesktopSupported()) {
                Desktop.getDesktop().open(OUTPUT_DIRECTORY.toFile());
            } else {
                throw new UnsupportedOperationException("A abertura de pastas não é suportada neste sistema.");
            }
        } catch (Exception exception) {
            showError("Não foi possível abrir a pasta.", rootMessage(exception));
        }
    }

    private void resetUpload() {
        selectedPdf = null;
        fileInfo.setText("Nenhum arquivo PDF selecionado.");
        processButton.setDisable(true);
        resultView.setVisible(false);
        resultView.setManaged(false);
        uploadView.setVisible(true);
        uploadView.setManaged(true);
    }

    private Path findSpreadsheet(Path directory) throws IOException {
        if (!Files.isDirectory(directory)) {
            throw new IllegalStateException("A pasta de modelos não existe: " + directory.toAbsolutePath());
        }
        try (Stream<Path> files = Files.walk(directory)) {
            return files.filter(Files::isRegularFile)
                    .filter(path -> path.getFileName().toString().toLowerCase().endsWith(".xlsx"))
                    .findFirst()
                    .orElseThrow(() -> new IllegalStateException("Nenhuma planilha .xlsx foi encontrada em " + directory));
        }
    }

    private void showError(String header, String content) {
        Alert alert = new Alert(Alert.AlertType.ERROR);
        alert.setTitle("Erro no processamento");
        alert.setHeaderText(header);
        alert.setContentText(content);
        alert.showAndWait();
    }

    private String rootMessage(Throwable exception) {
        Throwable cause = exception;
        while (cause.getCause() != null) {
            cause = cause.getCause();
        }
        return cause.getMessage() == null ? cause.getClass().getSimpleName() : cause.getMessage();
    }
}
