package app;

import extract.PdfBoxExtractor;

import java.io.File;
import java.io.IOException;

public class Main {
    public static void main (String[] args)  {
        String path = "src/resources/relatorio.pdf";
        File pdfFile = new File(path);

        PdfBoxExtractor pdfBoxExtractor = new PdfBoxExtractor();

        try{

           String textPDF= pdfBoxExtractor.extractRawText(pdfFile);
           System.out.println(textPDF);

        }catch (IllegalArgumentException e ){
            System.err.println("Erro de Validação: " + e.getMessage());
        } catch (IOException e){
            System.err.println("Erro de Leitura de Arquivo: " + e.getMessage());        }

    }
}
