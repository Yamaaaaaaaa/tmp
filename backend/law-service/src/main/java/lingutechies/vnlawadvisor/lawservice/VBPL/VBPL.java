package lingutechies.vnlawadvisor.lawservice.VBPL;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Entity
@Table(name = "vbpldaydu")
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VBPL {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(columnDefinition = "longtext")
    private String noidung;

    private String loai;

    @Column(length = 1000)
    private String ten;
}
