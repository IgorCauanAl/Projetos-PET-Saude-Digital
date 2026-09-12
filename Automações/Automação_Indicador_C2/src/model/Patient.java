package model;

import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

@Getter
@Setter
public class Patient {

    private String name;
    private LocalDate dateOfBirth;
    private String enrollment;
    private String cpf;
    private String ma;
    private String linkedProfessional;
    private Indicators indicators;


}
