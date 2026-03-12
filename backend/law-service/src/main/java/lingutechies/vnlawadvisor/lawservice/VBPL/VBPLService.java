package lingutechies.vnlawadvisor.lawservice.VBPL;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.util.Optional;
import java.util.List;

@Service
@RequiredArgsConstructor
public class VBPLService {
    private final VBPLRepository VBPLRepository;

    public Page<VBPL> getAllVBPL(Optional<Integer> pageNo, Optional<Integer> pageSize, Optional<String> loai, Optional<String> name){
        Pageable pageable = PageRequest.of(pageNo.orElse(0), pageSize.orElse(10));
        String loaiFilter = loai.filter(s -> !s.isBlank()).orElse(null);
        String nameFilter = name.filter(s -> !s.isBlank()).orElse(null);
        if (loaiFilter != null && nameFilter != null) {
            return VBPLRepository.findByLoaiAndTenContainingIgnoreCase(loaiFilter, nameFilter, pageable);
        } else if (loaiFilter != null) {
            return VBPLRepository.findByLoai(loaiFilter, pageable);
        } else if (nameFilter != null) {
            return VBPLRepository.findByTenContainingIgnoreCase(nameFilter, pageable);
        }
        return VBPLRepository.findAll(pageable);
    }

    public VBPL getVBPLbyID(Integer id){
        Optional<VBPL> optionalVBPL = VBPLRepository.findById(id);
        if (optionalVBPL.isPresent()) {
            return optionalVBPL.get();
        } else {
            return null;
        }
    }
}
