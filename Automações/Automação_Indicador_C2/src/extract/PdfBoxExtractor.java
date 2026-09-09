package extract;

import java.io.File;
import java.io.IOException;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

public class PdfBoxExtractor {

    //Limite máximo de 10MB por arquivo
    private static final long MAX_FILE_SIZE = 10* 1024 * 1024;

    public String extractRawText(File pdfFile) throws IOException {

        if(pdfFile == null || !pdfFile.exists()) {

            throw new IllegalArgumentException("Arquivo não encontrado");

        }


        if(pdfFile.length() > MAX_FILE_SIZE){
            throw new IllegalArgumentException("Arquivo excede o tamanho de 10 mb!");
        }


        try(PDDocument document = Loader.loadPDF(pdfFile)){

            PDFTextStripper stripper = new PDFTextStripper();
            String textPDF = stripper.getText(document);

            if(textPDF.trim().isEmpty()){
                throw new IllegalArgumentException("PDF não contem texto");
            }

            return textPDF;

        }

    }

}
